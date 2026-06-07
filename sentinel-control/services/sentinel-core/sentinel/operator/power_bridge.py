from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sentinel.mission.cancellation import CancellationToken
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerActuatorExecutor,
    PowerMissionPlan,
    PowerMissionTimeline,
    PowerRuntimeConfig,
    PowerRuntimeResult,
    PowerRuntimeStatus,
    PowerStepResult,
    PowerStepStatus,
    SentinelPowerRuntimeV0,
)

_GENERIC_BRIDGE_IRREVERSIBLE_MARKERS = {
    "api_mutation",
    "channel_send",
    "delete",
    "irreversible",
    "payment",
    "publish",
    "send_now",
    "spend",
    "trade",
    "transfer",
}
_CANONICAL_REQUEST_TARGET_KEYS = {
    "account",
    "account_id",
    "api_endpoint",
    "asset",
    "asset_id",
    "endpoint",
    "file_path",
    "merchant",
    "merchant_id",
    "page_url",
    "path",
    "recipient",
    "recipients",
    "target_path",
    "uri",
    "url",
}
_REQUEST_RUNTIME_VARIATION_KEYS = {
    "element_ref",
    "locator",
    "ref",
    "selector",
    "target_ref",
    "target_selector",
    "uid",
}
_TARGET_KEY_MARKERS = {
    "account",
    "asset",
    "destination",
    "domain",
    "endpoint",
    "host",
    "merchant",
    "path",
    "recipient",
    "target",
    "uri",
    "url",
}
_GENERIC_BRIDGE_MUTATION_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
_GENERIC_BRIDGE_SPECIAL_REQUEST_MARKERS = {
    "authority_ref",
    "credential_ref",
    "mutation_authority_ref",
    "payment_ref",
    "send_authority_ref",
}


@dataclass(frozen=True)
class BoundPowerActuatorExecutor:
    contract_id: str
    executor: PowerActuatorExecutor

    def __post_init__(self) -> None:
        if not self.contract_id.strip():
            raise ValueError("power actuator executor contract id required")


class OperatorPowerRuntimeBridge:
    def __init__(
        self,
        kernel: MissionKernel,
        *,
        runtime: SentinelPowerRuntimeV0 | None = None,
        telemetry_sink: object | None = None,
    ) -> None:
        self._kernel = kernel
        self._runtime = runtime or SentinelPowerRuntimeV0()
        self._telemetry_sink = telemetry_sink or getattr(kernel, "telemetry_sink", None)

    def run(
        self,
        mission_id: str,
        plan: PowerMissionPlan,
        *,
        envelope: MissionAuthorityEnvelope | None = None,
        executor_binding: BoundPowerActuatorExecutor | None = None,
        expected_executor_contract_id: str | None = None,
        actuator_executor: PowerActuatorExecutor | None = None,
        cancellation_token: CancellationToken | None = None,
        update_mission_status: bool = True,
    ) -> PowerRuntimeResult:
        if plan.mission_id != mission_id:
            raise ValueError("power plan mission_id must match operator mission_id")
        if not self._kernel.store.verify_record(mission_id):
            return self._emit(self._blocked_result(mission_id, "mission_record_tampered"))
        terminal_reason = self._kernel.terminal_block_reason(mission_id)
        if terminal_reason is not None:
            return self._emit(self._blocked_terminal_result(mission_id, terminal_reason))
        if envelope is None:
            return self._emit(self._blocked_result(mission_id, "mission_authority_envelope_required"))
        if envelope.revoked_at is not None or datetime.now(UTC) > envelope.resolved_expires_at():
            return self._emit(self._blocked_result(mission_id, "mission_authority_envelope_inactive"))
        if envelope.id != mission_id or not _plan_within_envelope(plan, envelope):
            return self._emit(self._blocked_result(mission_id, "power_plan_outside_authority"))
        if actuator_executor is not None:
            return self._emit(self._blocked_result(mission_id, "unbound_power_executor"))
        if executor_binding is not None and not isinstance(executor_binding, BoundPowerActuatorExecutor):
            return self._emit(self._blocked_result(mission_id, "unbound_power_executor"))
        if executor_binding is not None and (
            expected_executor_contract_id is not None
            and executor_binding.contract_id != expected_executor_contract_id
        ):
            return self._emit(self._blocked_result(mission_id, "executor_contract_mismatch"))
        reserved_actions = sum(1 + step.retry_budget for step in plan.graph.steps)
        reserved_cost = sum(step.estimated_cost_usd * (1 + step.retry_budget) for step in plan.graph.steps)
        try:
            self._kernel.store.reserve_power_budget(
                mission_id,
                action_count=reserved_actions,
                estimated_cost_usd=reserved_cost,
                max_actions=envelope.max_actions,
                max_cost_usd=envelope.max_cost_usd,
            )
        except ValueError:
            return self._emit(self._blocked_result(mission_id, "mission_power_budget_exhausted"))
        try:
            result = self._runtime.run(
                plan,
                config=PowerRuntimeConfig(enabled=True),
                actuator_executor=(
                    _proof_enforcing_executor(executor_binding.executor)
                    if executor_binding is not None
                    else None
                ),
                cancellation_token=cancellation_token,
            )
        except Exception:
            self._kernel.store.commit_power_budget(
                mission_id,
                reserved_actions=reserved_actions,
                reserved_cost_usd=reserved_cost,
                actual_actions=0,
                actual_cost_usd=0.0,
            )
            return self._emit(self._blocked_result(mission_id, "power_runtime_bridge_failure"))
        actual_actions = sum(result_item.attempt_count for result_item in result.step_results)
        self._kernel.store.commit_power_budget(
            mission_id,
            reserved_actions=reserved_actions,
            reserved_cost_usd=reserved_cost,
            actual_actions=actual_actions,
            actual_cost_usd=reserved_cost if actual_actions else 0.0,
        )
        if update_mission_status:
            status = _operator_status(result.status)
            self._kernel.update_status(mission_id, status, f"PowerRuntime finished with status {result.status.value}.")
        self._kernel.store.append_event(
            mission_id,
            event_type="power_runtime_result",
            safe_summary=f"PowerRuntime result {result.status.value}.",
            receipt_refs=list(result.receipt_refs),
            finalgate_certificate_refs=list(result.finalgate_certificate_refs),
            memory_feedback_refs=list(result.memory_feedback_refs),
            metadata={"power_runtime_status": result.status.value},
        )
        return self._emit(result, mission_id=mission_id)

    def _blocked_terminal_result(self, mission_id: str, terminal_reason: str) -> PowerRuntimeResult:
        return self._blocked_result(
            mission_id,
            "operator_mission_terminal",
            metadata={"drop_reason": "mission_closed", "mission_state": terminal_reason.rsplit(":", 1)[-1]},
        )

    def _emit(self, result: PowerRuntimeResult, *, mission_id: str | None = None) -> PowerRuntimeResult:
        if self._telemetry_sink is not None and hasattr(self._telemetry_sink, "record_power_runtime_result"):
            self._telemetry_sink.record_power_runtime_result(result, mission_id=mission_id or result.mission_id)
        return result

    def _blocked_result(
        self,
        mission_id: str,
        reason: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> PowerRuntimeResult:
        timeline = PowerMissionTimeline(mission_id=mission_id)
        timeline.record(
            "runtime_blocked",
            "Operator bridge blocked PowerRuntime before execution.",
            blocked_reason=reason,
        )
        self._kernel.store.append_event(
            mission_id,
            event_type="power_runtime_blocked",
            safe_summary="PowerRuntime blocked by the operator bridge before execution.",
            metadata={"drop_reason": reason, **(metadata or {})},
        )
        return PowerRuntimeResult(
            mission_id=mission_id,
            status=PowerRuntimeStatus.BLOCKED,
            timeline=timeline,
            blocked_reason=reason,
        )


def _operator_status(status: PowerRuntimeStatus) -> OperatorMissionStatus:
    if status is PowerRuntimeStatus.COMPLETED:
        return OperatorMissionStatus.COMPLETED
    if status is PowerRuntimeStatus.ABORTED:
        return OperatorMissionStatus.KILLED
    if status is PowerRuntimeStatus.BLOCKED:
        return OperatorMissionStatus.BLOCKED
    return OperatorMissionStatus.FAILED


def _plan_within_envelope(plan: PowerMissionPlan, envelope: MissionAuthorityEnvelope) -> bool:
    if not plan.graph.steps:
        return False
    worst_case_actions = sum(1 + step.retry_budget for step in plan.graph.steps)
    worst_case_cost = sum(step.estimated_cost_usd * (1 + step.retry_budget) for step in plan.graph.steps)
    recipient_count = sum(_recipient_count(step.request) for step in plan.graph.steps)
    if (
        worst_case_actions > envelope.max_actions
        or worst_case_cost > envelope.max_cost_usd
        or recipient_count > envelope.max_recipients
    ):
        return False
    allowed_actions = set(envelope.allowed_actions)
    forbidden_actions = set(envelope.forbidden_actions)
    allowed_tools = set(envelope.allowed_tools)
    allowed_systems = set(envelope.allowed_systems)
    for step in plan.graph.steps:
        if step.capability_level in {PowerActuatorCapabilityLevel.L6, PowerActuatorCapabilityLevel.L7}:
            return False
        if step.actuator_family is PowerActuatorFamily.CREDENTIAL_REF:
            return False
        if _matches_irreversible_marker(step.action_kind) or _matches_irreversible_marker(step.organ_kind):
            return False
        if _request_requires_special_authority(step.request):
            return False
        if step.action_kind not in allowed_actions or step.action_kind in forbidden_actions:
            return False
        if step.organ_kind not in allowed_tools:
            return False
        if step.actuator_family.value not in allowed_systems:
            return False
        if _contains_noncanonical_target_key(step.request):
            return False
        if not _request_within_envelope(step.request, envelope):
            return False
        if step.actuator_family is PowerActuatorFamily.WORKSPACE and not _contains_target_key(
            step.request,
            {"path", "file_path", "target_path"},
        ):
            return False
    return True


def _request_within_envelope(value: Any, envelope: MissionAuthorityEnvelope, *, key: str = "") -> bool:
    normalized_key = key.strip().lower()
    if isinstance(value, dict):
        return all(_request_within_envelope(item, envelope, key=str(child_key)) for child_key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return all(_request_within_envelope(item, envelope, key=normalized_key) for item in value)
    if value is None:
        return True
    text = str(value).strip()
    if normalized_key in {"url", "uri", "page_url", "endpoint", "api_endpoint"}:
        host = (urlparse(text if "://" in text else f"https://{text}").hostname or "").lower()
        allowed = {str(domain).strip().lower() for domain in envelope.allowed_domains}
        return bool(host) and any(host == domain or host.endswith(f".{domain}") for domain in allowed)
    if normalized_key in {"path", "file_path", "target_path"}:
        normalized = text.replace("\\", "/").strip("/")
        if ".." in normalized.split("/"):
            return False
        return any(
            normalized == allowed_path.replace("\\", "/").strip("/")
            or normalized.startswith(f"{allowed_path.replace('\\', '/').strip('/')}/")
            for allowed_path in envelope.allowed_paths
        )
    if normalized_key in {"account", "account_id", "recipient", "recipients"}:
        return text in {str(account) for account in envelope.allowed_accounts}
    return True


def _contains_target_key(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().lower() in keys or _contains_target_key(item, keys)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_contains_target_key(item, keys) for item in value)
    return False


def _contains_noncanonical_target_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if (
                normalized not in _CANONICAL_REQUEST_TARGET_KEYS
                and normalized not in _REQUEST_RUNTIME_VARIATION_KEYS
                and any(marker in normalized for marker in _TARGET_KEY_MARKERS)
            ):
                return True
            if _contains_noncanonical_target_key(item):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_noncanonical_target_key(item) for item in value)
    return False


def _recipient_count(value: Any, *, key: str = "") -> int:
    normalized_key = key.strip().lower()
    if isinstance(value, dict):
        return sum(_recipient_count(item, key=str(child_key)) for child_key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        if normalized_key in {"recipient", "recipients"}:
            return sum(1 for item in value if str(item).strip())
        return sum(_recipient_count(item, key=normalized_key) for item in value)
    if normalized_key in {"recipient", "recipients"} and value is not None and str(value).strip():
        return 1
    return 0


def _request_requires_special_authority(value: Any, *, key: str = "") -> bool:
    normalized_key = key.strip().lower()
    if normalized_key == "method" and str(value).strip().upper() in _GENERIC_BRIDGE_MUTATION_METHODS:
        return True
    if normalized_key in _GENERIC_BRIDGE_SPECIAL_REQUEST_MARKERS:
        return True
    if isinstance(value, dict):
        return any(_request_requires_special_authority(item, key=str(child_key)) for child_key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_request_requires_special_authority(item, key=normalized_key) for item in value)
    return False


def _proof_enforcing_executor(executor: PowerActuatorExecutor) -> PowerActuatorExecutor:
    def execute(step, context):
        result = executor(step, context)
        if (
            isinstance(result, PowerStepResult)
            and result.status is PowerStepStatus.SUCCEEDED
            and (not result.receipt_refs or not result.finalgate_certificate_refs)
        ):
            return PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.BLOCKED,
                blocked_reason="executor_success_proof_missing",
                safe_summary="Executor success lacked receipt and FinalGate proof.",
            )
        return result

    return execute


def _matches_irreversible_marker(value: str) -> bool:
    marker = value.strip().lower().replace("-", "_").replace(" ", "_")
    return any(
        marker == denied
        or marker.startswith(f"{denied}_")
        or marker.endswith(f"_{denied}")
        or f"_{denied}_" in marker
        for denied in _GENERIC_BRIDGE_IRREVERSIBLE_MARKERS
    )
