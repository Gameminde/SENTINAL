"""Tests for Task 5 / Wave D1.5 — Browser Receipt Wrapper Façade.

Locks in that :func:`wrap_browser_execution_receipt`:

* Preserves the legacy browser receipt's identity (no mutation, no
  subclass, ``id`` / ``receipt_hash`` unchanged).
* Routes through the official
  :meth:`OrganExecutionReceipt.started` factory — never forges a hash.
* Binds ``action_payload_hash`` to the paired dry-run.
* Raises :class:`ReceiptIntegrityError` on payload mismatch (via the
  factory, not swallowed).
* Encodes the legacy receipt reference under a documented
  ``browser-receipt://<Type>/<id>`` URI in ``output_ref`` and in the
  ``output_summary`` audit string.

A Hypothesis property test drives random matching / mutated payloads
to prove CP-3.2 (TOCTOU Prevention) also holds through the wrapper.
"""

from __future__ import annotations

import string
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import Field

from sentinel.organs import (
    ExternalOrganContract,
    OrganAuthorityEnvelope,
    OrganAuthorityEvaluator,
    OrganCapability,
    OrganDryRunReceipt,
    OrganKillSwitch,
    OrganPromotionLevel,
    OrganRiskProfiler,
    OrganType,
    VendorHarvestReference,
)
from sentinel.organs.browser.receipt_wrapper import (
    LEGACY_RECEIPT_URI_SCHEME,
    wrap_browser_execution_receipt,
)
from sentinel.organs.exceptions import ReceiptIntegrityError
from sentinel.organs.receipts import OrganExecutionReceipt
from sentinel.shared.events import EventBus
from sentinel.shared.models import SentinelModel, new_id
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Minimal stand-in for a legacy browser receipt. We intentionally do NOT
# import ``BrowserFormSubmitReceipt`` / ``BrowserV3Receipt`` subclasses here
# so the wrapper test is decoupled from the legacy-receipt schemas that
# Wave D3 will reshape. The wrapper's contract is "any SentinelModel with
# an ``id`` field" and this fixture tests exactly that contract.
# ---------------------------------------------------------------------------


class _FakeLegacyBrowserReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("fakelegacy"))
    mission_id: str
    action_label: str
    artifact_sha256: str
    trace_refs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Shared fixtures — build a fully consistent dry-run + authority +
# kill-switch triple that the ``started`` factory will accept.
# ---------------------------------------------------------------------------


def _mission(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_test",
        "mission_type": MissionType.GTM,
        "mission_title": "Wave D1.5 wrapper test",
        "mission_objective": "Wrap a legacy browser receipt.",
        "success_criteria": ["wrapped receipt exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_organ", "safe_file_writer"],
        "allowed_actions": ["browser_read_public_page", "write_trace"],
        "forbidden_actions": ["payment", "credential_access"],
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
        reason="Wrap legacy browser receipt.",
        preview=preview if preview is not None else {"url": "https://example.com"},
        evidence_refs=["ev_wrapper"],
    )
    executable = _executable_authority(authority)
    kill_switch = OrganKillSwitch(mission_id=env.id, organ_id=contract.id)
    return env, dry_run, executable, kill_switch


def _fake_receipt(mission_id: str) -> _FakeLegacyBrowserReceipt:
    return _FakeLegacyBrowserReceipt(
        mission_id=mission_id,
        action_label="browser_read_public_page",
        artifact_sha256="a" * 64,
        trace_refs=["legacy_trace_1", "legacy_trace_2"],
    )


# ---------------------------------------------------------------------------
# Identity and non-mutation.
# ---------------------------------------------------------------------------


def test_wrap_browser_receipt_preserves_legacy_receipt_identity():
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)
    legacy_id_before = legacy.id
    legacy_dump_before = legacy.model_dump()

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_wrap"],
    )

    # Legacy object is byte-identical after wrapping.
    assert legacy.id == legacy_id_before
    assert legacy.model_dump() == legacy_dump_before
    # Wrapped receipt points back at the legacy id via the URI.
    assert wrapped.output_ref is not None
    assert legacy.id in wrapped.output_ref


def test_wrap_browser_receipt_does_not_mutate_browser_receipt():
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)
    snapshot = legacy.model_copy(deep=True)

    wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_nomutate"],
    )

    # Field-by-field comparison against the pre-wrap snapshot.
    assert legacy.model_dump() == snapshot.model_dump()


def test_wrap_browser_receipt_rejects_legacy_receipt_without_id():
    """The wrapper refuses to produce a `browser-receipt://...` URI for a
    model with no meaningful id. A faux legacy object with an empty id
    must fail loudly rather than silently encoding an empty URI."""

    class _BadReceipt(SentinelModel):
        id: str = ""  # intentionally empty

    env, dry_run, authority, kill_switch = _build_run()
    bad = _BadReceipt()

    with pytest.raises(ValueError) as excinfo:
        wrap_browser_execution_receipt(
            browser_receipt=bad,
            dry_run=dry_run,
            authority=authority,
            kill_switch=kill_switch,
            execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
            trace_refs=["trace_bad"],
        )
    assert "id" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# Factory delegation and return type.
# ---------------------------------------------------------------------------


def test_wrap_browser_receipt_uses_organ_execution_receipt_factory():
    """The wrapper returns an :class:`OrganExecutionReceipt` produced by
    the ``started`` factory — NOT a hand-forged instance. The marker
    field ``execution_started`` is True (``planned_only`` would be
    False) and the ``receipt_hash`` matches the model's computed hash."""
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_factory"],
    )

    assert isinstance(wrapped, OrganExecutionReceipt)
    assert wrapped.execution_started is True
    assert wrapped.receipt_hash == wrapped.expected_receipt_hash()
    # Organ linkage preserved through the factory.
    assert wrapped.mission_id == dry_run.mission_id
    assert wrapped.organ_id == dry_run.organ_id
    assert wrapped.action == dry_run.action
    assert wrapped.dry_run_receipt_id == dry_run.id


def test_wrap_browser_receipt_binds_payload_hash_to_dry_run():
    """CP-3.1 (Payload Integrity) through the wrapper: matching payload
    yields ``wrapped.action_payload_hash == dry_run.action_payload_hash``."""
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_bind"],
    )

    assert wrapped.action_payload_hash == dry_run.action_payload_hash


def test_wrap_browser_receipt_rejects_payload_mismatch():
    """CP-3.2 (TOCTOU Prevention) through the wrapper: any payload
    drift produces :class:`ReceiptIntegrityError` via the factory."""
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    # Mutate the preview after dry-run creation — the classic TOCTOU case.
    mutated_payload = {
        "action": dry_run.action,
        "preview": {**dry_run.preview, "url": "https://attacker.example/"},
    }

    with pytest.raises(ReceiptIntegrityError) as excinfo:
        wrap_browser_execution_receipt(
            browser_receipt=legacy,
            dry_run=dry_run,
            authority=authority,
            kill_switch=kill_switch,
            execution_action_payload=mutated_payload,
            trace_refs=["trace_mismatch"],
        )
    assert "hash_mismatch" in str(excinfo.value)


def test_wrap_browser_receipt_rejects_added_key_mismatch():
    """Smuggling an extra key into the execution payload must also
    fail — not just URL mutation."""
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    smuggled_payload = {
        "action": dry_run.action,
        "preview": {**dry_run.preview, "smuggled_flag": "1"},
    }

    with pytest.raises(ReceiptIntegrityError):
        wrap_browser_execution_receipt(
            browser_receipt=legacy,
            dry_run=dry_run,
            authority=authority,
            kill_switch=kill_switch,
            execution_action_payload=smuggled_payload,
            trace_refs=["trace_smuggled"],
        )


# ---------------------------------------------------------------------------
# Output-ref and metadata carrying.
# ---------------------------------------------------------------------------


def test_wrap_browser_receipt_metadata_contains_legacy_type_and_id():
    """The ``output_summary`` string encodes the legacy class name and
    the legacy receipt id in a deterministic key=value shape so an
    auditor can grep for either."""
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_meta"],
        metadata={"k_alpha": "value_alpha", "k_beta": 42},
    )

    assert f"browser_receipt_type=_FakeLegacyBrowserReceipt" in wrapped.output_summary
    assert f"browser_receipt_id={legacy.id}" in wrapped.output_summary
    # Caller metadata surfaces, sorted by key for determinism.
    assert "k_alpha=value_alpha" in wrapped.output_summary
    assert "k_beta=42" in wrapped.output_summary
    # Separator is " | " per module contract.
    assert " | " in wrapped.output_summary


def test_wrap_browser_receipt_output_ref_uses_documented_uri_scheme():
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_uri"],
    )

    assert wrapped.output_ref is not None
    assert wrapped.output_ref.startswith(f"{LEGACY_RECEIPT_URI_SCHEME}://")
    assert wrapped.output_ref == (
        f"{LEGACY_RECEIPT_URI_SCHEME}://_FakeLegacyBrowserReceipt/{legacy.id}"
    )


# ---------------------------------------------------------------------------
# Event-bus integration (optional parameter, passes through).
# ---------------------------------------------------------------------------


def test_wrap_browser_receipt_emits_trace_event_when_event_bus_provided():
    env, dry_run, authority, kill_switch = _build_run()
    legacy = _fake_receipt(env.id)
    bus = EventBus(env.id)

    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_bus_caller"],
        event_bus=bus,
    )

    # The factory appends its own event id to trace_refs when a bus is supplied.
    assert len(wrapped.trace_refs) >= 2
    assert "trace_bus_caller" in wrapped.trace_refs


# ---------------------------------------------------------------------------
# Property test — random matching payloads succeed; mutated ones fail.
# ---------------------------------------------------------------------------


_URL = st.sampled_from(
    [
        "https://example.com",
        "https://example.com/docs",
        "https://example.com/research/page",
    ]
)
_EXTRA_VALUE = st.text(
    alphabet=string.ascii_letters + string.digits, min_size=1, max_size=12
)
_EXTRA_KEY = st.sampled_from(["viewport", "user_agent", "locale", "referrer"])


@given(
    url=_URL,
    extra_key=_EXTRA_KEY,
    extra_value=_EXTRA_VALUE,
    mutation_suffix=st.text(alphabet=string.ascii_letters, min_size=1, max_size=6),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_wrap_browser_receipt_property_matching_succeeds_mutation_fails(
    url: str, extra_key: str, extra_value: str, mutation_suffix: str
):
    """For any generated ``preview`` dict:

    * Wrapping with the unmutated payload succeeds and the wrapped
      receipt's ``action_payload_hash`` equals the dry-run's.
    * Wrapping with a payload whose preview has an extra key or a
      mutated URL raises :class:`ReceiptIntegrityError`.
    """
    preview = {"url": url, extra_key: extra_value}
    env, dry_run, authority, kill_switch = _build_run(preview=preview)
    legacy = _fake_receipt(env.id)

    # Matching payload succeeds.
    wrapped = wrap_browser_execution_receipt(
        browser_receipt=legacy,
        dry_run=dry_run,
        authority=authority,
        kill_switch=kill_switch,
        execution_action_payload={"action": dry_run.action, "preview": dry_run.preview},
        trace_refs=["trace_match"],
    )
    assert wrapped.action_payload_hash == dry_run.action_payload_hash

    # Mutated URL fails.
    mutated_preview = {**preview, "url": f"{url}/{mutation_suffix}"}
    with pytest.raises(ReceiptIntegrityError):
        wrap_browser_execution_receipt(
            browser_receipt=legacy,
            dry_run=dry_run,
            authority=authority,
            kill_switch=kill_switch,
            execution_action_payload={
                "action": dry_run.action,
                "preview": mutated_preview,
            },
            trace_refs=["trace_match_mut"],
        )


# ---------------------------------------------------------------------------
# Public API surface.
# ---------------------------------------------------------------------------


def test_public_api_exports_wrapper_and_scheme_constant():
    from sentinel.organs.browser import receipt_wrapper as module

    assert hasattr(module, "wrap_browser_execution_receipt")
    assert hasattr(module, "LEGACY_RECEIPT_URI_SCHEME")
    assert module.LEGACY_RECEIPT_URI_SCHEME == "browser-receipt"
