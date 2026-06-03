from __future__ import annotations

from types import SimpleNamespace

from sentinel.agent import AgentEventType, ArtifactCaptureSandbox, EventBus
from sentinel.agent.browser import (
    BrowserAccessibilitySnapshotBuilder,
    BrowserControlledCapabilityRunner,
    BrowserFormSubmitBackendResult,
    BrowserFormSubmitExecutor,
    BrowserFormSubmitRequest,
    BrowserInteractionIntent,
    BrowserInteractionStep,
    BrowserInteractionTarget,
    BrowserRenderedPage,
    BrowserV3AuthorityClass,
    BrowserV3AuthorityGrant,
)
from sentinel.agent.browser.interaction_dry_run import BrowserInteractionDryRunPlanner
from sentinel.agent.final_gate import CoreFinalGate
from sentinel.agent.llm import (
    ContextPack,
    ContextPackActionIntent,
    ContextPackAuthorityBoundary,
    ContextPackPromptInjectionFlag,
    ContextPackStableRef,
    ToolIntentCompiler,
)
from sentinel.agent.phases import AgentPhase
from sentinel.agent.tool_call_protocol import CanonicalToolCall
from sentinel.capabilities import default_tool_registry
from sentinel.capabilities.risk import ToolSideEffect
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs.browser.controlled_runner import _bool_arg
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_v3_form_submit"
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake"


def test_controlled_runner_boolean_arguments_do_not_treat_false_strings_as_true() -> None:
    assert _bool_arg("false", default=False) is False
    assert _bool_arg("false", default=True) is False
    assert _bool_arg("true", default=False) is True
    assert _bool_arg("not-a-bool", default=False) is False
    assert _bool_arg("not-a-bool", default=True) is True


def grant(**overrides) -> BrowserV3AuthorityGrant:
    data = {
        "id": "grant_form_submit",
        "authority_class": BrowserV3AuthorityClass.FORM_SUBMIT,
        "allowed_domains": ["example.com"],
        "max_uses": 1,
    }
    data.update(overrides)
    return BrowserV3AuthorityGrant(**data)


def envelope(*, include_grant: bool = True, **overrides) -> MissionAuthorityEnvelope:
    authority_grants = [grant().model_dump(mode="json")] if include_grant else []
    data = {
        "id": MISSION_ID,
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Browser V3 form submit",
        "mission_objective": "Submit one public form from a certified proof chain.",
        "success_criteria": ["Form submit receipt exists"],
        "mode": MissionMode.POWER,
        "risk_appetite_score": 90,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_public_form_submit"],
        "allowed_actions": ["browser_form_submit"],
        "forbidden_actions": ["browser_private_session", "browser_login_authority", "browser_download_quarantine"],
        "allowed_paths": ["data/generated_projects"],
        "allowed_domains": ["example.com"],
        "browser_v3_authority_grants": authority_grants,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def snapshot():
    html = """
    <html><body>
      <main>
        <h1>Contact</h1>
        <input type="text" placeholder="Email" />
        <button>Send request</button>
      </main>
    </body></html>
    """
    return BrowserAccessibilitySnapshotBuilder().build(html=html, text="Contact Email Send request")


def first_ref(snap, role: str) -> str:
    for ref_id, ref in snap.refs.items():
        if ref.role == role:
            return ref_id
    raise AssertionError(f"missing ref for role {role}")


def append_snapshot_event(bus: EventBus, snap) -> str:
    event = bus.append(
        AgentEventType.BROWSER_SNAPSHOT_CAPTURED,
        "Rendered browser snapshot captured.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        payload={
            "receipt_id": "receipt_snapshot",
            "snapshot_artifact_id": "artifact_snapshot",
            "snapshot_artifact_sha256": "a" * 64,
            "accessibility_snapshot_sha256": snap.snapshot_sha256,
            "accessibility_page_sha256": snap.page_sha256,
            "accessibility_ref_count": snap.stats.refs,
            "accessibility_interactive_count": snap.stats.interactive,
            "accessibility_ref_ids": sorted(snap.refs),
        },
    )
    return event.id


def create_plan(bus: EventBus, snap):
    snapshot_event_id = append_snapshot_event(bus, snap)
    textbox = first_ref(snap, "textbox")
    button = first_ref(snap, "button")
    result = BrowserInteractionDryRunPlanner().create_plan(
        mission_id=MISSION_ID,
        snapshot=snap,
        steps=[
            BrowserInteractionStep(
                intent=BrowserInteractionIntent.FILL_PLAN,
                target=BrowserInteractionTarget(ref=textbox),
                text="lead@example.com",
                reason="Fill public form field.",
            ),
            BrowserInteractionStep(
                intent=BrowserInteractionIntent.CLICK_PLAN,
                target=BrowserInteractionTarget(ref=button),
                reason="Commit the public form after authority checks.",
            ),
        ],
        event_bus=bus,
        final_url="https://example.com/form",
        snapshot_trace_id=snapshot_event_id,
    )
    assert result.accepted is True
    assert result.plan is not None
    return result.plan, result.trace_event_id, snapshot_event_id, textbox, button


def context_pack(snap, textbox: str, button: str, *, injection: bool = False) -> ContextPack:
    source_id = "source_1"
    refs = [
        ContextPackStableRef(
            id=textbox,
            source_id=source_id,
            selector=f"accessibility_ref:{textbox}",
            digest="d" * 64,
            page_sha256=snap.page_sha256,
            snapshot_sha256=snap.snapshot_sha256,
        ),
        ContextPackStableRef(
            id=button,
            source_id=source_id,
            selector=f"accessibility_ref:{button}",
            digest="e" * 64,
            page_sha256=snap.page_sha256,
            snapshot_sha256=snap.snapshot_sha256,
        ),
    ]
    return ContextPack(
        context_pack_id="cpk_formsubmit01",
        mission_id=MISSION_ID,
        mission_goal="Submit one public form from a certified proof chain.",
        authority_boundary=ContextPackAuthorityBoundary(
            allowed_actions=["browser_form_submit"],
            forbidden_actions=["browser_private_session", "browser_login_authority", "browser_download_quarantine"],
            allowed_tools=["browser_public_form_submit"],
            allowed_domains=["example.com"],
        ),
        browser_stable_refs=refs,
        available_action_intents=[
            ContextPackActionIntent(
                id="act_submit",
                kind="browser_form_submit",
                impact="external_public_commit",
                authorization_conditions=["browser_v3_authority_grant"],
            )
        ],
        prompt_injection_flags=[
            ContextPackPromptInjectionFlag(source_id=source_id, risk="high", indicators=["tool_instruction"], blocked=True, sanitized=True)
        ]
        if injection
        else [],
    )


def compile_submit_intent(bus: EventBus, pack: ContextPack, env: MissionAuthorityEnvelope, snap, textbox: str, button: str):
    raw = {
        "tool_id": "browser_public_form_submit",
        "action": "browser_form_submit",
        "capability": "public_web_form_submit",
        "target": "https://example.com/form",
        "requested_side_effects": ["network_read", "network_write", "browser_read", "browser_submit", "filesystem_write", "local_draft_write"],
        "arguments": {
            "context_pack_id": pack.context_pack_id,
            "context_pack_sha256": pack.context_pack_sha256,
            "authority_grant_id": "grant_form_submit",
            "stable_ref_ids": [textbox, button],
            "page_sha256": snap.page_sha256,
            "snapshot_sha256": snap.snapshot_sha256,
            "submit_kind": "submit",
            "expected_effect": "confirmation text appears",
        },
    }
    return ToolIntentCompiler().compile(raw, pack, env, event_bus=bus)


def sandbox(tmp_path) -> ArtifactCaptureSandbox:
    return ArtifactCaptureSandbox(mission_id=MISSION_ID, capture_root=tmp_path / "captures")


class FakeFormSubmitBackend:
    def __init__(self, before_snapshot, *, after_url="https://example.com/form/thanks", after_text="Thanks, request received.", submitted=True):
        self.before_snapshot = before_snapshot
        self.after_url = after_url
        self.after_text = after_text
        self.submitted = submitted

    def __call__(self, request: BrowserFormSubmitRequest) -> BrowserFormSubmitBackendResult:
        return BrowserFormSubmitBackendResult(
            before_snapshot=self.before_snapshot,
            after_page=BrowserRenderedPage(
                final_url=self.after_url,
                status_code=200,
                title="Thanks",
                text=self.after_text,
                links=[],
                html=f"<html><body><main><h1>{self.after_text}</h1></main></body></html>",
                screenshot_png=PNG_BYTES,
            ),
            final_url_before=request.final_url,
            final_url_after=self.after_url,
            submitted=self.submitted,
            submitted_ref_ids=[request.form_ref_id, request.submit_ref_id],
        )


def v3_check(trace):
    return CoreFinalGate._browser_v3_form_submit_contract(SimpleNamespace(trace=tuple(trace)))


def test_form_submit_accepted_with_full_authority_and_proof(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)
    env = envelope()
    pack = context_pack(snap, textbox, button)
    compiled = compile_submit_intent(bus, pack, env, snap, textbox, button)
    assert compiled.accepted is True
    assert compiled.trace_event_id is not None

    result = BrowserFormSubmitExecutor(backend=FakeFormSubmitBackend(snap)).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id=pack.context_pack_id,
            compiled_intent_trace_id=compiled.trace_event_id,
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
        policy_trace_id="policy_1",
    )

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.submit_ref_id == button
    assert result.artifact_ids
    assert bus.events()[-1].event_type == AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED
    assert v3_check(bus.events()).passed is True


def test_form_submit_rejects_backend_final_url_outside_grant(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)

    result = BrowserFormSubmitExecutor(
        backend=FakeFormSubmitBackend(snap, after_url="https://evil.example/form/thanks")
    ).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
            allow_cross_origin=True,
        ),
        authority_grant=grant(allow_cross_origin=True),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )

    assert result.accepted is False
    assert result.reason == "browser_form_submit_backend_url_outside_authority"
    assert all("evil.example" not in error for error in result.errors)


def test_controlled_runner_rejects_form_submit_without_v3_authority(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)
    call = CanonicalToolCall(
        tool_id="browser_public_form_submit",
        action="browser_form_submit",
        capability="public_web_form_submit",
        target="https://example.com/form",
        requested_side_effects=[
            ToolSideEffect.NETWORK_READ,
            ToolSideEffect.NETWORK_WRITE,
            ToolSideEffect.BROWSER_READ,
            ToolSideEffect.BROWSER_SUBMIT,
            ToolSideEffect.FILESYSTEM_WRITE,
            ToolSideEffect.LOCAL_DRAFT_WRITE,
        ],
        arguments={
            "plan": plan.model_dump(mode="json"),
            "authority_grant_id": "grant_form_submit",
            "context_pack_id": "cpk_formsubmit01",
            "compiled_intent_trace_id": "compiled_trace",
            "plan_trace_event_id": plan_trace_id,
            "before_snapshot_trace_event_id": snapshot_trace_id,
            "final_url": "https://example.com/form",
            "form_ref_id": textbox,
            "submit_ref_id": button,
            "expected_effect": "confirmation text appears",
        },
        canonical_hash="hash",
    )

    result = BrowserControlledCapabilityRunner(
        registry=default_tool_registry(),
        capture_root=tmp_path / "captures",
        form_submit_backend=FakeFormSubmitBackend(snap),
    ).run(call, envelope(include_grant=False), event_bus=bus)

    assert result.accepted is False
    assert result.reason == "black_zone_side_effect"


def test_stale_ref_snapshot_is_rejected(tmp_path):
    snap = snapshot()
    stale = BrowserAccessibilitySnapshotBuilder().build(html="<html><body><button>Other</button></body></html>", text="Other")
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)

    result = BrowserFormSubmitExecutor(backend=FakeFormSubmitBackend(stale)).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )

    assert result.accepted is False
    assert result.reason == "browser_form_submit_stale_snapshot"


def test_prompt_injected_source_cannot_compile_submit_intent():
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    textbox = first_ref(snap, "textbox")
    button = first_ref(snap, "button")
    env = envelope()
    pack = context_pack(snap, textbox, button, injection=True)

    result = compile_submit_intent(bus, pack, env, snap, textbox, button)

    assert result.accepted is False
    assert any("runtime_ref_from_injection_source" in error for error in result.errors)


def test_cross_origin_submit_is_rejected_without_grant(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)

    result = BrowserFormSubmitExecutor(backend=FakeFormSubmitBackend(snap, after_url="https://other.example/thanks")).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )

    assert result.accepted is False
    assert result.reason == "browser_form_submit_cross_origin_result"


def test_missing_pre_snapshot_and_missing_post_snapshot_rejected(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, _, textbox, button = create_plan(bus, snap)

    missing_pre = BrowserFormSubmitExecutor(backend=FakeFormSubmitBackend(snap)).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id="",
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )

    assert missing_pre.accepted is False
    assert "missing_before_snapshot_trace_event_id" in missing_pre.errors

    class MissingPostBackend(FakeFormSubmitBackend):
        def __call__(self, request: BrowserFormSubmitRequest) -> BrowserFormSubmitBackendResult:
            result = super().__call__(request)
            return result.model_copy(update={"after_page": None})

    missing_post = BrowserFormSubmitExecutor(backend=MissingPostBackend(snap)).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id="before_trace",
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )

    assert missing_post.accepted is False
    assert missing_post.reason == "browser_form_submit_post_snapshot_missing"


def test_final_gate_rejects_forged_form_submit_receipt(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    plan, plan_trace_id, snapshot_trace_id, textbox, button = create_plan(bus, snap)
    compiled = bus.append(
        AgentEventType.TOOL_INTENT_COMPILED,
        "compiled",
        phase_before=AgentPhase.TOOL_SELECTING,
        phase_after=AgentPhase.TOOL_SELECTING,
        payload={"accepted": True, "context_pack_id": "cpk_formsubmit01", "canonical_hash": "c", "compilation_hash": "d"},
    )
    result = BrowserFormSubmitExecutor(backend=FakeFormSubmitBackend(snap)).execute(
        BrowserFormSubmitRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_form_submit",
            context_pack_id="cpk_formsubmit01",
            compiled_intent_trace_id=compiled.id,
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/form",
            form_ref_id=textbox,
            submit_ref_id=button,
            expected_effect="confirmation text appears",
        ),
        authority_grant=grant(),
        event_bus=bus,
        artifact_capture=sandbox(tmp_path),
    )
    assert result.accepted is True
    events = list(bus.events())
    payload = dict(events[-1].payload)
    payload["post_submit_snapshot_artifact_sha256"] = "0" * 64
    events[-1] = events[-1].model_copy(update={"payload": payload})

    check = v3_check(events)

    assert check.passed is False
    assert any("browser_v3_form_submit_post_snapshot_artifact_hash_mismatch" in error for error in check.details["errors"])


def test_raw_llm_submit_call_and_other_v3_power_are_rejected():
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    textbox = first_ref(snap, "textbox")
    button = first_ref(snap, "button")
    env = envelope()
    pack = context_pack(snap, textbox, button)

    raw_missing_contract = {
        "tool_id": "browser_public_form_submit",
        "action": "browser_form_submit",
        "requested_side_effects": ["browser_submit"],
        "arguments": {"ref_id": button},
    }
    submit_result = ToolIntentCompiler().compile(raw_missing_contract, pack, env, event_bus=bus)
    assert submit_result.accepted is False
    assert "missing_or_mismatched_context_pack_id" in submit_result.errors

    raw_download = {
        "tool_id": "browser_public_form_submit",
        "action": "browser_download_quarantine",
        "requested_side_effects": ["browser_submit"],
        "arguments": {
            "context_pack_id": pack.context_pack_id,
            "context_pack_sha256": pack.context_pack_sha256,
        },
    }
    download_result = ToolIntentCompiler().compile(raw_download, pack, env, event_bus=bus)
    assert download_result.accepted is False
    assert any("non_delegated_browser_power" in error or "action_outside_mission_authority" in error for error in download_result.errors)
