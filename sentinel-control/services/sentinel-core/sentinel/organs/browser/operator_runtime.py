from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from sentinel.agent.action_engine import ActionEngine, CompiledMissionPolicyCompiler, SceneActionCandidate  # noqa: E402 — agent-layer cognitive bridge (Wave D documented exception)
from sentinel.agent.browser.perception_adapter import BrowserPerceptionAdapter  # noqa: E402 — agent-layer cognitive bridge, intentionally kept in agent (Wave D documented exception)
from sentinel.agent.perception import PerceptionSourceType  # noqa: E402 — agent-layer cognitive bridge (Wave D documented exception)
from sentinel.agent.tool_call_protocol import CanonicalToolCall  # noqa: E402 — agent-layer cognitive bridge (Wave D documented exception)
from sentinel.capabilities.registry import ToolRegistry
from sentinel.mission.models import MissionAction, MissionAuthorityEnvelope
from sentinel.organs.browser.controlled_runner import BrowserControlledCapabilityRunner
from sentinel.organs.browser.models import BrowserControlledCapabilityResult, BrowserControlledCapabilityStatus
from sentinel.organs.browser.ui_observation import BrowserUIObservationSet
from sentinel.organs.browser.visual_observation import BrowserVisualObservation
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserOperatorRuntimeStatus(StrEnum):
    PREPARED = "prepared"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"


class BrowserOperatorRouteResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("boproute"))
    mission_id: str
    accepted: bool
    status: BrowserOperatorRuntimeStatus
    reason: str
    tool_id: str
    action: str
    perception_frame_id: str | None = None
    perception_frame_sha256: str | None = None
    compiled_policy_id: str | None = None
    compiled_policy_hash: str | None = None
    candidate_id: str | None = None
    action_envelope_id: str | None = None
    target_ref_id: str | None = None
    controlled_result: BrowserControlledCapabilityResult
    trace_event_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BrowserOperatorRouteProtocol(Protocol):
    def run(
        self,
        call: CanonicalToolCall,
        envelope: MissionAuthorityEnvelope,
        *,
        event_bus: EventBus,
        capture_root: str | Path | None = None,
    ) -> BrowserOperatorRouteResult:
        ...

    def run_mission_action(
        self,
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        *,
        capture_root: str | Path | None = None,
    ) -> dict[str, Any]:
        ...


class BrowserOperatorRuntimeRoute:
    """Runtime bridge from mission policy to the existing Browser V3 runner.

    This route does not add browser capability. It requires a pre-existing
    browser action, a perception observation set, and an authority envelope that
    already grants the action/tool pair.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        capture_root: str | Path | None = None,
        **browser_runner_kwargs: Any,
    ) -> None:
        self.registry = registry
        self.capture_root = Path(capture_root).resolve() if capture_root is not None else None
        self.browser_runner_kwargs = dict(browser_runner_kwargs)
        self.action_engine = ActionEngine()
        self.policy_compiler = CompiledMissionPolicyCompiler()
        self.perception_adapter = BrowserPerceptionAdapter()

    def run(
        self,
        call: CanonicalToolCall,
        envelope: MissionAuthorityEnvelope,
        *,
        event_bus: EventBus,
        capture_root: str | Path | None = None,
    ) -> BrowserOperatorRouteResult:
        if event_bus.mission_id != envelope.id:
            raise ValueError("Browser operator runtime route event bus mission_id must match the envelope.")
        start = event_bus.append(
            AgentEventType.BROWSER_OPERATOR_ROUTE_STARTED,
            "Browser operator runtime route started.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": call.tool_id,
                "action": call.action,
                "canonical_hash": call.canonical_hash,
                "target": call.target,
            },
        )

        if call.action not in BrowserControlledCapabilityRunner.SUPPORTED_ACTIONS:
            return self._reject(
                call,
                envelope,
                event_bus,
                reason="browser_operator_action_not_supported",
                trace_refs=[start.id],
            )

        observation_set = self._observation_set(call.arguments)
        if observation_set is None:
            return self._reject(
                call,
                envelope,
                event_bus,
                reason="browser_operator_observation_missing",
                trace_refs=[start.id],
            )
        if observation_set.mission_id != envelope.id:
            return self._reject(
                call,
                envelope,
                event_bus,
                reason="browser_operator_observation_mission_mismatch",
                trace_refs=[start.id],
            )

        observation_event = self._record_ui_observation(event_bus, observation_set, trace_refs=[start.id])
        target_ref_id = self._target_ref_id(call)
        if not target_ref_id:
            return self._reject(
                call,
                envelope,
                event_bus,
                reason="browser_operator_target_ref_missing",
                trace_refs=[start.id, observation_event.id],
            )

        visuals = self._visual_observations(call.arguments)
        frame = self.perception_adapter.build_frame(
            ui_observation_set=observation_set,
            visual_observations=visuals,
            action_classes_by_ref={target_ref_id: [call.action]},
        )
        target = frame.target_by_ref(target_ref_id)
        if target is None:
            return self._reject(
                call,
                envelope,
                event_bus,
                reason="browser_operator_target_ref_not_observed",
                trace_refs=[start.id, observation_event.id, *frame.trace_refs],
            )

        policy = self.policy_compiler.compile(envelope, trace_refs=[start.id, observation_event.id, *frame.trace_refs])
        compiled_call, compiled_event_id = self._ensure_compiled_intent_event(call, event_bus, trace_refs=[start.id, observation_event.id])
        candidate = SceneActionCandidate(
            mission_id=envelope.id,
            perception_frame_id=frame.id,
            source_type=PerceptionSourceType.BROWSER,
            target_id=target.id,
            runtime_ref_id=target_ref_id,
            action_class=compiled_call.action,
            tool_id=compiled_call.tool_id,
            intent=str(compiled_call.arguments.get("operator_intent") or f"Route {compiled_call.action} through Browser Operator."),
            expected_effect=str(compiled_call.arguments.get("expected_effect") or compiled_call.action),
            confidence_score=target.confidence.overall,
            required_confidence=float(compiled_call.arguments.get("required_confidence") or 0.0),
            planned_step_count=int(compiled_call.arguments.get("planned_step_count") or 1),
            actions_already_used=int(compiled_call.arguments.get("actions_already_used") or 0),
            repair_attempt_count=int(compiled_call.arguments.get("repair_attempt_count") or 0),
            arguments=dict(compiled_call.arguments),
            evidence_refs=[start.id, observation_event.id, compiled_event_id],
        )
        prepared = self.action_engine.prepare_browser_action(
            frame=frame,
            candidate=candidate,
            policy=policy,
            canonical_call=compiled_call,
        )
        if not prepared.accepted or prepared.envelope is None:
            return self._reject(
                compiled_call,
                envelope,
                event_bus,
                reason=f"browser_operator_prepare_failed:{prepared.reason}",
                errors=prepared.errors,
                trace_refs=[start.id, observation_event.id, compiled_event_id],
                frame_id=frame.id,
                frame_hash=frame.frame_sha256,
                policy_id=policy.id,
                policy_hash=policy.policy_hash,
                candidate_id=candidate.id,
                target_ref_id=target_ref_id,
            )

        prepared_event = event_bus.append(
            AgentEventType.BROWSER_OPERATOR_ROUTE_PREPARED,
            "Browser operator runtime route prepared an ActionEnvelope.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": compiled_call.tool_id,
                "action": compiled_call.action,
                "perception_frame_id": frame.id,
                "perception_frame_sha256": frame.frame_sha256,
                "compiled_policy_id": policy.id,
                "compiled_policy_hash": policy.policy_hash,
                "candidate_id": candidate.id,
                "action_envelope_id": prepared.envelope.id,
                "target_ref_id": target_ref_id,
                "decision": prepared.decision.value,
            },
            trace_refs=[start.id, observation_event.id, compiled_event_id],
        )

        runner = self._browser_runner(capture_root)
        executed = self.action_engine.execute_browser_action(
            action_envelope=prepared.envelope,
            mission_envelope=envelope,
            runner=runner,
            event_bus=event_bus,
        )
        controlled = executed.controlled_result
        if controlled is None:
            controlled = self._controlled_rejection(
                compiled_call,
                event_bus,
                reason=executed.reason,
                errors=executed.errors,
                trace_refs=[start.id, prepared_event.id],
            )
        if not executed.accepted:
            rejected = event_bus.append(
                AgentEventType.BROWSER_OPERATOR_ROUTE_REJECTED,
                "Browser operator runtime route was rejected by ActionEngine or the browser runner.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "tool_id": compiled_call.tool_id,
                    "action": compiled_call.action,
                    "reason": executed.reason,
                    "errors": executed.errors,
                    "controlled_trace_event_id": controlled.trace_event_id,
                    "perception_frame_id": frame.id,
                    "compiled_policy_id": policy.id,
                    "action_envelope_id": prepared.envelope.id,
                },
                trace_refs=[start.id, prepared_event.id, controlled.trace_event_id] if controlled.trace_event_id else [start.id, prepared_event.id],
            )
            return BrowserOperatorRouteResult(
                mission_id=envelope.id,
                accepted=False,
                status=BrowserOperatorRuntimeStatus.REJECTED,
                reason=executed.reason,
                tool_id=compiled_call.tool_id,
                action=compiled_call.action,
                perception_frame_id=frame.id,
                perception_frame_sha256=frame.frame_sha256,
                compiled_policy_id=policy.id,
                compiled_policy_hash=policy.policy_hash,
                candidate_id=candidate.id,
                action_envelope_id=prepared.envelope.id,
                target_ref_id=target_ref_id,
                controlled_result=controlled,
                trace_event_ids=[start.id, observation_event.id, compiled_event_id, prepared_event.id, rejected.id],
                errors=executed.errors,
            )

        completed = event_bus.append(
            AgentEventType.BROWSER_OPERATOR_ROUTE_COMPLETED,
            "Browser operator runtime route completed through the existing Browser runner.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": compiled_call.tool_id,
                "action": compiled_call.action,
                "reason": executed.reason,
                "receipt_id": controlled.receipt_id,
                "browser_trace_event_id": controlled.browser_trace_event_id,
                "perception_frame_id": frame.id,
                "compiled_policy_id": policy.id,
                "action_envelope_id": prepared.envelope.id,
                "target_ref_id": target_ref_id,
            },
            trace_refs=[
                ref
                for ref in [start.id, observation_event.id, compiled_event_id, prepared_event.id, controlled.browser_trace_event_id]
                if ref
            ],
        )
        return BrowserOperatorRouteResult(
            mission_id=envelope.id,
            accepted=True,
            status=BrowserOperatorRuntimeStatus.EXECUTED,
            reason=executed.reason,
            tool_id=compiled_call.tool_id,
            action=compiled_call.action,
            perception_frame_id=frame.id,
            perception_frame_sha256=frame.frame_sha256,
            compiled_policy_id=policy.id,
            compiled_policy_hash=policy.policy_hash,
            candidate_id=candidate.id,
            action_envelope_id=prepared.envelope.id,
            target_ref_id=target_ref_id,
            controlled_result=controlled,
            trace_event_ids=[start.id, observation_event.id, compiled_event_id, prepared_event.id, completed.id],
        )

    def run_mission_action(
        self,
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        *,
        capture_root: str | Path | None = None,
    ) -> dict[str, Any]:
        call = self._canonical_call_from_action(action)
        bus = EventBus(envelope.id)
        result = self.run(call, envelope, event_bus=bus, capture_root=capture_root)
        return {
            "status": result.status.value,
            "accepted": result.accepted,
            "reason": result.reason,
            "tool_id": result.tool_id,
            "action": result.action,
            "receipt_id": result.controlled_result.receipt_id,
            "artifact_ids": result.controlled_result.artifact_ids,
            "browser_trace_event_id": result.controlled_result.browser_trace_event_id,
            "operator_trace_event_ids": result.trace_event_ids,
            "operator_event_types": [event.event_type.value for event in bus.events()],
            "operator_trace_certified": bus.verify_chain(),
        }

    def _browser_runner(self, capture_root: str | Path | None) -> BrowserControlledCapabilityRunner:
        root = Path(capture_root).resolve() if capture_root is not None else self.capture_root
        if root is None:
            root = Path.cwd().resolve() / "data" / "generated_projects" / "browser_operator_runtime"
        return BrowserControlledCapabilityRunner(
            registry=self.registry,
            capture_root=root,
            **self.browser_runner_kwargs,
        )

    def _reject(
        self,
        call: CanonicalToolCall,
        envelope: MissionAuthorityEnvelope,
        event_bus: EventBus,
        *,
        reason: str,
        errors: list[str] | None = None,
        trace_refs: list[str] | None = None,
        frame_id: str | None = None,
        frame_hash: str | None = None,
        policy_id: str | None = None,
        policy_hash: str | None = None,
        candidate_id: str | None = None,
        target_ref_id: str | None = None,
    ) -> BrowserOperatorRouteResult:
        controlled = self._controlled_rejection(call, event_bus, reason=reason, errors=errors or [], trace_refs=trace_refs or [])
        event = event_bus.append(
            AgentEventType.BROWSER_OPERATOR_ROUTE_REJECTED,
            "Browser operator runtime route rejected before execution.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": call.tool_id,
                "action": call.action,
                "reason": reason,
                "errors": errors or [],
                "controlled_trace_event_id": controlled.trace_event_id,
                "perception_frame_id": frame_id,
                "compiled_policy_id": policy_id,
                "candidate_id": candidate_id,
                "target_ref_id": target_ref_id,
            },
            trace_refs=[ref for ref in [*(trace_refs or []), controlled.trace_event_id] if ref],
        )
        return BrowserOperatorRouteResult(
            mission_id=envelope.id,
            accepted=False,
            status=BrowserOperatorRuntimeStatus.REJECTED,
            reason=reason,
            tool_id=call.tool_id,
            action=call.action,
            perception_frame_id=frame_id,
            perception_frame_sha256=frame_hash,
            compiled_policy_id=policy_id,
            compiled_policy_hash=policy_hash,
            candidate_id=candidate_id,
            target_ref_id=target_ref_id,
            controlled_result=controlled,
            trace_event_ids=[*(trace_refs or []), event.id],
            errors=errors or [],
        )

    @staticmethod
    def _controlled_rejection(
        call: CanonicalToolCall,
        event_bus: EventBus,
        *,
        reason: str,
        errors: list[str],
        trace_refs: list[str],
    ) -> BrowserControlledCapabilityResult:
        event = event_bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
            "Browser operator controlled capability request rejected.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": call.tool_id,
                "action": call.action,
                "reason": reason,
                "errors": errors,
            },
            trace_refs=trace_refs,
        )
        return BrowserControlledCapabilityResult(
            accepted=False,
            status=BrowserControlledCapabilityStatus.REJECTED,
            tool_id=call.tool_id,
            action=call.action,
            reason=reason,
            trace_event_id=event.id,
            errors=errors,
        )

    @staticmethod
    def _record_ui_observation(event_bus: EventBus, observation_set: BrowserUIObservationSet, *, trace_refs: list[str]) -> Any:
        return event_bus.append(
            AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED,
            "Browser operator route received a mission-scoped UI observation set.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "observation_set_id": observation_set.id,
                "observation_sha256": observation_set.observation_sha256,
                "observation_set": observation_set.model_dump(mode="json"),
                "source": "runtime_route",
                "source_count": observation_set.source_count,
                "observation_count": len(observation_set.observations),
                "url": observation_set.url,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
            trace_refs=trace_refs,
        )

    @staticmethod
    def _observation_set(arguments: dict[str, Any]) -> BrowserUIObservationSet | None:
        raw = arguments.get("ui_observation_set")
        if not isinstance(raw, dict):
            return None
        try:
            return BrowserUIObservationSet(**raw)
        except Exception:
            return None

    @staticmethod
    def _visual_observations(arguments: dict[str, Any]) -> list[BrowserVisualObservation]:
        raw_items = arguments.get("visual_observations") or []
        if not isinstance(raw_items, list):
            return []
        observations: list[BrowserVisualObservation] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                observations.append(BrowserVisualObservation(**item))
            except Exception:
                continue
        return observations

    @staticmethod
    def _target_ref_id(call: CanonicalToolCall) -> str:
        arguments = call.arguments
        for key in (
            "target_ref_id",
            "ref_id",
            "submit_ref_id",
            "upload_ref_id",
            "login_ref_id",
            "source_ref_id",
            "form_ref_id",
        ):
            value = arguments.get(key)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _ensure_compiled_intent_event(
        call: CanonicalToolCall,
        event_bus: EventBus,
        *,
        trace_refs: list[str],
    ) -> tuple[CanonicalToolCall, str]:
        existing = str(call.arguments.get("compiled_intent_trace_id") or "")
        known = {event.id for event in event_bus.events() if event.event_type == AgentEventType.TOOL_INTENT_COMPILED}
        if existing and existing in known:
            return call, existing
        context_pack_id = str(call.arguments.get("context_pack_id") or f"runtime_context_{call.id}")
        context_pack_hash = _hash_payload(
            {
                "context_pack_id": context_pack_id,
                "tool_id": call.tool_id,
                "action": call.action,
                "canonical_hash": call.canonical_hash,
                "source": "browser_operator_runtime_route",
            }
        )
        validated_ids = {
            str(event.payload.get("context_pack_id"))
            for event in event_bus.events()
            if event.event_type == AgentEventType.CONTEXT_PACK_VALIDATED and event.payload.get("accepted") is True
        }
        if context_pack_id not in validated_ids:
            assembled = event_bus.append(
                AgentEventType.CONTEXT_PACK_ASSEMBLED,
                "Browser operator route assembled a minimal runtime ContextPack boundary.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "context_pack_id": context_pack_id,
                    "context_pack_sha256": context_pack_hash,
                    "source": "browser_operator_runtime_route",
                },
                trace_refs=trace_refs,
            )
            event_bus.append(
                AgentEventType.CONTEXT_PACK_VALIDATED,
                "Browser operator route validated the runtime ContextPack boundary.",
                phase_before=AgentPhase.EXECUTING,
                phase_after=AgentPhase.EXECUTING,
                payload={
                    "accepted": True,
                    "context_pack_id": context_pack_id,
                    "context_pack_sha256": context_pack_hash,
                    "errors": [],
                    "source": "browser_operator_runtime_route",
                },
                trace_refs=[*trace_refs, assembled.id],
            )
        event = event_bus.append(
            AgentEventType.TOOL_INTENT_COMPILED,
            "Browser operator route compiled the canonical call into a mission-bound action intent.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "accepted": True,
                "tool_id": call.tool_id,
                "action": call.action,
                "canonical_hash": call.canonical_hash,
                "compilation_hash": _hash_payload({"canonical_hash": call.canonical_hash, "context_pack_sha256": context_pack_hash}),
                "context_pack_id": context_pack_id,
                "source": "browser_operator_runtime_route",
            },
            trace_refs=trace_refs,
        )
        arguments = {**call.arguments, "compiled_intent_trace_id": event.id}
        return _call_with_arguments(call, arguments), event.id

    @staticmethod
    def _canonical_call_from_action(action: MissionAction) -> CanonicalToolCall:
        payload = action.input.get("tool_call") or action.input.get("canonical_call")
        if not isinstance(payload, dict):
            raise ValueError("browser_operator_route_action_missing_tool_call")
        arguments = payload.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError("browser_operator_route_action_arguments_invalid")
        requested = payload.get("requested_side_effects") or []
        canonical_payload = {
            "tool_id": str(payload.get("tool_id") or action.tool),
            "action": str(payload.get("action") or ""),
            "arguments": arguments,
            "capability": payload.get("capability"),
            "target": payload.get("target") or action.target,
            "requested_side_effects": [str(item.value if hasattr(item, "value") else item) for item in requested],
        }
        return CanonicalToolCall(
            tool_id=canonical_payload["tool_id"],
            action=canonical_payload["action"],
            arguments=arguments,
            capability=canonical_payload["capability"],
            target=canonical_payload["target"],
            requested_side_effects=[],
            canonical_hash=str(payload.get("canonical_hash") or _hash_payload(canonical_payload)),
        )


def _call_with_arguments(call: CanonicalToolCall, arguments: dict[str, Any]) -> CanonicalToolCall:
    payload = {
        "tool_id": call.tool_id,
        "action": call.action,
        "arguments": arguments,
        "capability": call.capability,
        "target": call.target,
        "requested_side_effects": [effect.value for effect in call.requested_side_effects],
    }
    return call.model_copy(update={"arguments": arguments, "canonical_hash": _hash_payload(payload)})


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
