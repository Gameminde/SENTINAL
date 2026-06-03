from __future__ import annotations

from types import SimpleNamespace

from sentinel.agent import AgentEventType, ArtifactCaptureSandbox, EventBus
from sentinel.agent.browser import (
    BrowserAccessibilitySnapshotBuilder,
    BrowserControlledCapabilityRunner,
    BrowserInteractionIntent,
    BrowserInteractionStep,
    BrowserInteractionTarget,
    BrowserRenderedPage,
    BrowserUploadAuthorizedExecutor,
    BrowserUploadAuthorizedRequest,
    BrowserUploadBackendResult,
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
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_v3_upload"
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake"
ARTIFACT_BYTES = b"%PDF-1.7\nupload candidate\n%%EOF"


def grant(*, artifact_id: str = "capt_source", **overrides) -> BrowserV3AuthorityGrant:
    data = {
        "id": "grant_upload",
        "authority_class": BrowserV3AuthorityClass.UPLOAD_AUTHORIZED,
        "allowed_domains": ["example.com"],
        "allowed_artifact_ids": [artifact_id],
        "allowed_mime_types": ["application/pdf"],
        "max_bytes": 1024,
        "blocked_flow_types": ["payment", "credential", "login", "download"],
    }
    data.update(overrides)
    return BrowserV3AuthorityGrant(**data)


def envelope(*, artifact_id: str = "capt_source", include_grant: bool = True, **overrides) -> MissionAuthorityEnvelope:
    authority_grants = [grant(artifact_id=artifact_id).model_dump(mode="json")] if include_grant else []
    data = {
        "id": MISSION_ID,
        "user_id": "user_001",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "Browser V3 authorized upload",
        "mission_objective": "Upload one certified artifact to a public endpoint.",
        "success_criteria": ["Upload receipt exists"],
        "mode": MissionMode.POWER,
        "risk_appetite_score": 90,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_upload_authorized"],
        "allowed_actions": ["browser_upload_authorized"],
        "forbidden_actions": ["browser_private_session", "browser_login_authority", "browser_js_evaluate_sandboxed"],
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
        <input type="file" aria-label="Upload file" />
        <button>Upload</button>
      </main>
    </body></html>
    """
    return BrowserAccessibilitySnapshotBuilder().build(html=html, text="Upload file Upload")


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
    upload_ref = first_ref(snap, "button")
    result = BrowserInteractionDryRunPlanner().create_plan(
        mission_id=MISSION_ID,
        snapshot=snap,
        steps=[
            BrowserInteractionStep(
                intent=BrowserInteractionIntent.CLICK_PLAN,
                target=BrowserInteractionTarget(ref=upload_ref),
                reason="Use certified artifact on public upload control.",
            )
        ],
        event_bus=bus,
        final_url="https://example.com/upload",
        snapshot_trace_id=snapshot_event_id,
    )
    assert result.accepted is True
    assert result.plan is not None
    return result.plan, result.trace_event_id, snapshot_event_id, upload_ref


def context_pack(snap, upload_ref: str, *, injection: bool = False) -> ContextPack:
    source_id = "source_upload"
    return ContextPack(
        context_pack_id="cpk_upload01",
        mission_id=MISSION_ID,
        mission_goal="Upload one certified artifact to a public endpoint.",
        authority_boundary=ContextPackAuthorityBoundary(
            allowed_actions=["browser_upload_authorized"],
            forbidden_actions=["browser_private_session", "browser_login_authority", "browser_js_evaluate_sandboxed"],
            allowed_tools=["browser_upload_authorized"],
            allowed_domains=["example.com"],
        ),
        browser_stable_refs=[
            ContextPackStableRef(
                id=upload_ref,
                source_id=source_id,
                selector=f"accessibility_ref:{upload_ref}",
                digest="d" * 64,
                page_sha256=snap.page_sha256,
                snapshot_sha256=snap.snapshot_sha256,
            )
        ],
        available_action_intents=[
            ContextPackActionIntent(
                id="act_upload",
                kind="browser_upload_authorized",
                impact="external_public_upload",
                authorization_conditions=["browser_v3_authority_grant", "certified_artifact_id"],
            )
        ],
        prompt_injection_flags=[
            ContextPackPromptInjectionFlag(source_id=source_id, risk="high", indicators=["upload_instruction"], blocked=True, sanitized=True)
        ]
        if injection
        else [],
    )


def compile_upload_intent(bus: EventBus, pack: ContextPack, env: MissionAuthorityEnvelope, snap, upload_ref: str, artifact):
    raw = {
        "tool_id": "browser_upload_authorized",
        "action": "browser_upload_authorized",
        "capability": "public_web_upload_authorized",
        "target": "https://example.com/upload",
        "requested_side_effects": [
            "network_read",
            "network_write",
            "browser_read",
            "filesystem_read",
            "filesystem_write",
            "local_draft_write",
        ],
        "arguments": {
            "context_pack_id": pack.context_pack_id,
            "context_pack_sha256": pack.context_pack_sha256,
            "authority_grant_id": "grant_upload",
            "upload_ref_id": upload_ref,
            "page_sha256": snap.page_sha256,
            "snapshot_sha256": snap.snapshot_sha256,
            "source_artifact_id": artifact.id,
            "source_artifact_sha256": artifact.sha256,
            "expected_effect": "upload confirmation appears",
        },
    }
    return ToolIntentCompiler().compile(raw, pack, env, event_bus=bus)


def sandbox(tmp_path) -> ArtifactCaptureSandbox:
    return ArtifactCaptureSandbox(mission_id=MISSION_ID, capture_root=tmp_path / "captures")


def source_artifact(sbox: ArtifactCaptureSandbox, bus: EventBus):
    result = sbox.capture_binary(
        relative_path="browser/download_quarantine/source.pdf",
        data=ARTIFACT_BYTES,
        artifact_type="browser_download_quarantine",
        content_type="application/pdf",
        event_bus=bus,
        phase=AgentPhase.EXECUTING,
    )
    assert result.accepted is True
    assert result.artifact is not None
    return result.artifact


class FakeUploadBackend:
    def __init__(self, before_snapshot, *, after_url="https://example.com/upload/thanks", after_text="Upload complete.", uploaded=True):
        self.before_snapshot = before_snapshot
        self.after_url = after_url
        self.after_text = after_text
        self.uploaded = uploaded

    def __call__(self, request: BrowserUploadAuthorizedRequest) -> BrowserUploadBackendResult:
        return BrowserUploadBackendResult(
            before_snapshot=self.before_snapshot,
            after_page=BrowserRenderedPage(
                final_url=self.after_url,
                status_code=200,
                title="Upload complete",
                text=self.after_text,
                links=[],
                html=f"<html><body><main><h1>{self.after_text}</h1></main></body></html>",
                screenshot_png=PNG_BYTES,
            ),
            final_url_before=request.final_url,
            final_url_after=self.after_url,
            uploaded=self.uploaded,
            uploaded_ref_ids=[request.upload_ref_id],
        )


def v3_check(trace):
    return CoreFinalGate._browser_v3_upload_authorized_contract(SimpleNamespace(trace=tuple(trace)))


def test_upload_authorized_accepted_with_full_authority_and_proof(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    env = envelope(artifact_id=artifact.id)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)
    pack = context_pack(snap, upload_ref)
    compiled = compile_upload_intent(bus, pack, env, snap, upload_ref, artifact)
    assert compiled.accepted is True
    assert compiled.trace_event_id is not None

    result = BrowserUploadAuthorizedExecutor(backend=FakeUploadBackend(snap)).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id=pack.context_pack_id,
            compiled_intent_trace_id=compiled.trace_event_id,
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=artifact,
            expected_effect="upload confirmation appears",
        ),
        authority_grant=grant(artifact_id=artifact.id),
        event_bus=bus,
        artifact_capture=sbox,
        policy_trace_id="policy_1",
    )

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.source_artifact_id == artifact.id
    assert result.artifact_ids
    assert bus.events()[-1].event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED
    assert v3_check(bus.events()).passed is True


def test_upload_authorized_rejects_backend_final_url_outside_grant(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)

    result = BrowserUploadAuthorizedExecutor(
        backend=FakeUploadBackend(snap, after_url="https://evil.example/upload/thanks")
    ).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id="cpk_upload01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=artifact,
            expected_effect="upload confirmation appears",
            allow_cross_origin=True,
        ),
        authority_grant=grant(artifact_id=artifact.id, allow_cross_origin=True),
        event_bus=bus,
        artifact_capture=sbox,
    )

    assert result.accepted is False
    assert result.reason == "browser_upload_backend_url_outside_authority"
    assert all("evil.example" not in error for error in result.errors)


def test_controlled_runner_rejects_upload_without_v3_authority(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)
    call = CanonicalToolCall(
        tool_id="browser_upload_authorized",
        action="browser_upload_authorized",
        capability="public_web_upload_authorized",
        target="https://example.com/upload",
        requested_side_effects=[
            ToolSideEffect.NETWORK_READ,
            ToolSideEffect.NETWORK_WRITE,
            ToolSideEffect.BROWSER_READ,
            ToolSideEffect.FILESYSTEM_READ,
            ToolSideEffect.FILESYSTEM_WRITE,
            ToolSideEffect.LOCAL_DRAFT_WRITE,
        ],
        arguments={
            "plan": plan.model_dump(mode="json"),
            "source_artifact": artifact.model_dump(mode="json"),
            "authority_grant_id": "grant_upload",
            "context_pack_id": "cpk_upload01",
            "compiled_intent_trace_id": "compiled_trace",
            "plan_trace_event_id": plan_trace_id,
            "before_snapshot_trace_event_id": snapshot_trace_id,
            "final_url": "https://example.com/upload",
            "upload_ref_id": upload_ref,
            "expected_effect": "upload confirmation appears",
        },
        canonical_hash="hash",
    )

    result = BrowserControlledCapabilityRunner(
        registry=default_tool_registry(),
        capture_root=tmp_path / "captures_runner",
        upload_backend=FakeUploadBackend(snap),
    ).run(call, envelope(include_grant=False), event_bus=bus)

    assert result.accepted is False
    assert result.reason in {"action_not_granted_by_mission_authority", "browser_v3_authority_grant_missing"}


def test_upload_rejects_ungranted_artifact_and_missing_trace(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)

    ungranted = BrowserUploadAuthorizedExecutor(backend=FakeUploadBackend(snap)).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id="cpk_upload01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=artifact,
            expected_effect="upload confirmation appears",
        ),
        authority_grant=grant(artifact_id="other_artifact"),
        event_bus=bus,
        artifact_capture=sbox,
    )
    assert ungranted.accepted is False
    assert "source_artifact_not_granted" in ungranted.errors

    missing_trace_artifact = artifact.model_copy(update={"trace_refs": []})
    missing_trace = BrowserUploadAuthorizedExecutor(backend=FakeUploadBackend(snap)).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id="cpk_upload01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=missing_trace_artifact,
            expected_effect="upload confirmation appears",
        ),
        authority_grant=grant(artifact_id=artifact.id),
        event_bus=bus,
        artifact_capture=sbox,
    )
    assert missing_trace.accepted is False
    assert "source_artifact_missing_trace_ref" in missing_trace.errors


def test_prompt_injected_source_cannot_compile_upload_intent(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    upload_ref = first_ref(snap, "button")
    env = envelope(artifact_id=artifact.id)
    pack = context_pack(snap, upload_ref, injection=True)

    result = compile_upload_intent(bus, pack, env, snap, upload_ref, artifact)

    assert result.accepted is False
    assert any("runtime_ref_from_injection_source" in error for error in result.errors)


def test_cross_origin_upload_is_rejected_without_grant(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)

    result = BrowserUploadAuthorizedExecutor(backend=FakeUploadBackend(snap, after_url="https://other.example/uploaded")).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id="cpk_upload01",
            compiled_intent_trace_id="compiled_trace",
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=artifact,
            expected_effect="upload confirmation appears",
        ),
        authority_grant=grant(artifact_id=artifact.id),
        event_bus=bus,
        artifact_capture=sbox,
    )

    assert result.accepted is False
    assert result.reason == "browser_upload_cross_origin_result"


def test_final_gate_rejects_forged_upload_source_artifact(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    plan, plan_trace_id, snapshot_trace_id, upload_ref = create_plan(bus, snap)
    compiled = bus.append(
        AgentEventType.TOOL_INTENT_COMPILED,
        "compiled",
        payload={"accepted": True, "context_pack_id": "cpk_upload01", "canonical_hash": "c", "compilation_hash": "d"},
    )
    result = BrowserUploadAuthorizedExecutor(backend=FakeUploadBackend(snap)).execute(
        BrowserUploadAuthorizedRequest(
            mission_id=MISSION_ID,
            authority_grant_id="grant_upload",
            context_pack_id="cpk_upload01",
            compiled_intent_trace_id=compiled.id,
            plan=plan,
            plan_trace_event_id=plan_trace_id or "",
            before_snapshot_trace_event_id=snapshot_trace_id,
            final_url="https://example.com/upload",
            upload_ref_id=upload_ref,
            source_artifact=artifact,
            expected_effect="upload confirmation appears",
        ),
        authority_grant=grant(artifact_id=artifact.id),
        event_bus=bus,
        artifact_capture=sbox,
    )
    assert result.accepted is True
    events = list(bus.events())
    payload = dict(events[-1].payload)
    payload["source_artifact_sha256"] = "0" * 64
    events[-1] = events[-1].model_copy(update={"payload": payload})

    check = v3_check(events)

    assert check.passed is False
    assert any("browser_v3_upload_source_artifact_hash_mismatch" in error for error in check.details["errors"])


def test_raw_llm_upload_call_and_other_v3_power_are_rejected(tmp_path):
    snap = snapshot()
    bus = EventBus(MISSION_ID)
    sbox = sandbox(tmp_path)
    artifact = source_artifact(sbox, bus)
    upload_ref = first_ref(snap, "button")
    env = envelope(artifact_id=artifact.id)
    pack = context_pack(snap, upload_ref)

    raw_missing_contract = {
        "tool_id": "browser_upload_authorized",
        "action": "browser_upload_authorized",
        "requested_side_effects": ["network_write", "filesystem_read"],
        "arguments": {"upload_ref_id": upload_ref, "source_artifact_id": artifact.id},
    }
    upload_result = ToolIntentCompiler().compile(raw_missing_contract, pack, env, event_bus=bus)
    assert upload_result.accepted is False
    assert "missing_or_mismatched_context_pack_id" in upload_result.errors

    raw_private = {
        "tool_id": "browser_upload_authorized",
        "action": "browser_private_session",
        "requested_side_effects": ["network_write", "filesystem_read"],
        "arguments": {
            "context_pack_id": pack.context_pack_id,
            "context_pack_sha256": pack.context_pack_sha256,
        },
    }
    private_result = ToolIntentCompiler().compile(raw_private, pack, env, event_bus=bus)
    assert private_result.accepted is False
    assert any("non_delegated_browser_power" in error or "action_outside_mission_authority" in error for error in private_result.errors)
