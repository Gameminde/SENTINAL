"""Task 3 / Requirement 3 — Dry-Run to Execution Cryptographic Binding (F-A3.9).

Closes the TOCTOU window between ``OrganDryRunReceipt`` creation and
``OrganExecutionReceipt`` creation. Doctrine:

    ∀ execution: execution.action_payload_hash == dry_run.action_payload_hash

If the action payload changes between dry-run approval and execution, the
``OrganExecutionReceipt.started(...)`` factory raises
``ReceiptIntegrityError`` with the code ``execution_action_payload_hash_mismatch``.

**Validates: Requirement 3 (CP-3.1 Payload Integrity, CP-3.2 TOCTOU Prevention)**
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs import (
    ExternalOrganContract,
    OrganAuthorityEnvelope,
    OrganAuthorityEvaluator,
    OrganCapability,
    OrganDryRunReceipt,
    OrganExecutionReceipt,
    OrganKillSwitch,
    OrganPromotionLevel,
    OrganRiskProfiler,
    OrganType,
    VendorHarvestReference,
)
from sentinel.organs.exceptions import ReceiptIntegrityError
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Fixtures — duplicated minimally from ``tests/test_p6_external_organ_foundry.py``
# to keep this module self-contained.
# ---------------------------------------------------------------------------


def _mission(**overrides: Any) -> MissionAuthorityEnvelope:
    data: dict[str, Any] = {
        "user_id": "user_toctou",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "TOCTOU binding test",
        "mission_objective": "Prove dry-run payload matches execution payload.",
        "success_criteria": ["Dry-run exists", "Execution certified"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_organ", "safe_file_writer"],
        "allowed_actions": ["browser_read_public_page", "write_trace"],
        "forbidden_actions": ["payment", "trade_order", "credential_access", "account_create"],
        "allowed_domains": ["example.com"],
        "allowed_accounts": [],
        "max_actions": 12,
        "max_cost_usd": 2.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _contract() -> ExternalOrganContract:
    return ExternalOrganContract(
        organ_name="browser_power_governor",
        organ_type=OrganType.BROWSER,
        description="Classifies and governs browser powers without direct execution.",
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        capabilities=[
            OrganCapability(
                name="browser_reliability",
                description="Plan browser reliability profiles.",
                actions=["browser_read_public_page"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["src_cloak_readme"],
            )
        ],
        supported_actions=["browser_read_public_page", "browser_submit"],
        authority_fields=["allowed_domains", "allowed_actions"],
        source_refs=[
            VendorHarvestReference(
                source_system="CloakBrowser",
                source_url="https://github.com/CloakHQ/CloakBrowser",
                mechanism="Playwright-compatible browser reliability and fingerprint controls.",
                sentinel_rewrite="BrowserPowerGovernor",
                risk_notes=["misuse objectives require classification"],
                evidence_refs=["src_cloak_readme"],
            )
        ],
    )


def _executable_authority(base: OrganAuthorityEnvelope) -> OrganAuthorityEnvelope:
    """Promote a dry-run authority to an executable authority (L6)."""
    return OrganAuthorityEnvelope(
        id=base.id,
        mission_id=base.mission_id,
        root_authority_id=base.root_authority_id,
        organ_id=base.organ_id,
        organ_name=base.organ_name,
        allowed_actions=base.allowed_actions,
        allowed_tools=base.allowed_tools,
        allowed_domains=base.allowed_domains,
        allowed_accounts=base.allowed_accounts,
        allowed_paths=base.allowed_paths,
        max_actions=base.max_actions,
        max_cost_usd=base.max_cost_usd,
        execution_authorized=True,
        dry_run_only=False,
    )


def _build_run(
    preview: dict[str, Any] | None = None,
    action: str = "browser_read_public_page",
):
    env = _mission()
    contract = _contract()
    authority = OrganAuthorityEvaluator().evaluate(
        env, contract, requested_actions=[action]
    )
    risk = OrganRiskProfiler().profile(contract, authority, action=action)
    dry_run = OrganDryRunReceipt.create(
        authority,
        risk,
        reason="Preview.",
        preview=preview if preview is not None else {"url": "https://example.com"},
        evidence_refs=["ev"],
    )
    executable = _executable_authority(authority)
    kill_switch = OrganKillSwitch(mission_id=env.id, organ_id=contract.id)
    return env, contract, dry_run, executable, kill_switch


# ---------------------------------------------------------------------------
# Test 1 — matching payload succeeds
# ---------------------------------------------------------------------------


def test_matching_payload_hash_succeeds() -> None:
    """**Validates: CP-3.1 (Payload Integrity).**

    Constructing an ``OrganExecutionReceipt`` via ``started(...)`` with an
    ``execution_action_payload`` equal to the dry-run's payload succeeds and
    the returned receipt carries the same ``action_payload_hash`` as the
    dry-run receipt.
    """
    _, _, dry_run, executable, kill_switch = _build_run()

    receipt = OrganExecutionReceipt.started(
        dry_run,
        executable,
        kill_switch,
        promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
        output_summary="Matching payload.",
        trace_refs=["trace_1"],
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
    )

    assert receipt.execution_started is True
    assert receipt.action_payload_hash == dry_run.action_payload_hash
    assert receipt.action_payload_hash  # non-empty


# ---------------------------------------------------------------------------
# Test 2 — mutated payload raises ReceiptIntegrityError
# ---------------------------------------------------------------------------


def test_mutated_payload_raises_integrity_error() -> None:
    """**Validates: CP-3.2 (TOCTOU Prevention).**

    Mutating the preview between dry-run approval and execution raises
    ``ReceiptIntegrityError`` with the canonical
    ``execution_action_payload_hash_mismatch`` code.
    """
    _, _, dry_run, executable, kill_switch = _build_run()

    with pytest.raises(ReceiptIntegrityError) as excinfo:
        OrganExecutionReceipt.started(
            dry_run,
            executable,
            kill_switch,
            promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            output_summary="Mutated payload.",
            trace_refs=["trace_1"],
            execution_action_payload={
                "action": dry_run.action,
                "preview": {"url": "https://evil.example"},
            },
        )
    assert "execution_action_payload_hash_mismatch" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Test 3 — planned_only passes through dry-run action_payload_hash
# ---------------------------------------------------------------------------


def test_planned_only_carries_dry_run_action_payload_hash() -> None:
    """``planned_only`` does not execute and thus trivially carries the
    dry-run's ``action_payload_hash`` onto the execution receipt.

    No ``execution_action_payload`` is required because no execution occurs.
    """
    _, _, dry_run, _, _ = _build_run()

    execution = OrganExecutionReceipt.planned_only(
        dry_run,
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        output_summary="No execution.",
    )

    assert execution.action_payload_hash == dry_run.action_payload_hash
    assert execution.execution_started is False


# ---------------------------------------------------------------------------
# Test 4 — started() requires execution_action_payload as a keyword arg
# ---------------------------------------------------------------------------


def test_started_requires_execution_action_payload() -> None:
    """Calling ``started(...)`` without ``execution_action_payload=`` raises
    ``TypeError`` (missing required keyword). The kwarg has no default and
    MUST NOT be silently omitted by adapter code.
    """
    _, _, dry_run, executable, kill_switch = _build_run()

    with pytest.raises(TypeError):
        OrganExecutionReceipt.started(  # type: ignore[call-arg]
            dry_run,
            executable,
            kill_switch,
            promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            output_summary="Missing payload.",
            trace_refs=["trace_1"],
        )


# ---------------------------------------------------------------------------
# Test 5 — Hypothesis property: payload equivalence succeeds, mutation fails
# ---------------------------------------------------------------------------


_ACTION_POOL = st.sampled_from(["browser_read_public_page"])
_URL_POOL = st.sampled_from(
    [
        "https://example.com",
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c/d",
    ]
)
_EXTRA_KEY_POOL = st.sampled_from(["user_agent", "referer", "cookies", "headers"])
_EXTRA_VALUE_POOL = st.sampled_from(
    ["Mozilla/5.0", "none", "{}", "empty", "sentinel", ""]
)
_MUTATION_URL_POOL = st.sampled_from(
    [
        "https://evil.example",
        "https://example.com/mutated",
        "https://example.com/?x=1",
    ]
)


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    action=_ACTION_POOL,
    url=_URL_POOL,
    extra_key=_EXTRA_KEY_POOL,
    extra_value=_EXTRA_VALUE_POOL,
    mutation_url=_MUTATION_URL_POOL,
)
def test_toctou_property(
    action: str,
    url: str,
    extra_key: str,
    extra_value: str,
    mutation_url: str,
) -> None:
    """**Validates: CP-3.1 (Payload Integrity) and CP-3.2 (TOCTOU Prevention).**

    For any generated ``(action, preview)`` pair:

    * Case A: ``execution_action_payload`` equals dry-run payload → receipt
      is constructed and ``receipt.action_payload_hash == dry_run.action_payload_hash``.
    * Case B: ``execution_action_payload`` differs (either url mutated or an
      extra key added) → ``ReceiptIntegrityError`` is raised.
    """
    preview = {"url": url, extra_key: extra_value}
    _, _, dry_run, executable, kill_switch = _build_run(preview=preview, action=action)

    # Case A — matching payload succeeds.
    matching_receipt = OrganExecutionReceipt.started(
        dry_run,
        executable,
        kill_switch,
        promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
        output_summary="Property matching.",
        trace_refs=["trace_1"],
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
    )
    assert matching_receipt.action_payload_hash == dry_run.action_payload_hash

    # Case B1 — mutated url raises.
    mutated_preview = {**preview, "url": mutation_url}
    # Skip the degenerate sample where the "mutation" happens to equal the
    # original url — nothing has been mutated, so no integrity error is
    # expected. This is an input-space filter, not a weakened assertion.
    if mutated_preview != preview:
        with pytest.raises(ReceiptIntegrityError):
            OrganExecutionReceipt.started(
                dry_run,
                executable,
                kill_switch,
                promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
                output_summary="Property mutated url.",
                trace_refs=["trace_1"],
                execution_action_payload={
                    "action": dry_run.action,
                    "preview": mutated_preview,
                },
            )

    # Case B2 — added key raises.
    added_key_preview = {**preview, "sentinel_smuggled_flag": "1"}
    with pytest.raises(ReceiptIntegrityError):
        OrganExecutionReceipt.started(
            dry_run,
            executable,
            kill_switch,
            promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            output_summary="Property added key.",
            trace_refs=["trace_1"],
            execution_action_payload={
                "action": dry_run.action,
                "preview": added_key_preview,
            },
        )
