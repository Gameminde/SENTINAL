from __future__ import annotations

import hashlib
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.desktop_sidecar_models import (
    DesktopActionApproval,
    DesktopActionKind,
    DesktopActionPreview,
    DesktopActionProposal,
    DesktopActionRequest,
    DesktopActionResult,
    DesktopAppRef,
    DesktopAppSnapshot,
    DesktopBeforeAfterEvidence,
    DesktopClockSnapshot,
    DesktopControlMode,
    DesktopDisplayRef,
    DesktopFinalGateDecision,
    DesktopHardwareMetricSnapshot,
    DesktopKillSwitchBinding,
    DesktopMetricValue,
    DesktopMonitoringReceipt,
    DesktopMonitoringResult,
    DesktopObservationRequest,
    DesktopObservationResult,
    DesktopPermissionPolicy,
    DesktopProcessSnapshot,
    DesktopRedactionResult,
    DesktopRegionRef,
    DesktopRevocationCheck,
    DesktopScreenshotRef,
    DesktopSensorSnapshot,
    DesktopSidecarConfig,
    DesktopSidecarFinalGateCertificate,
    DesktopSidecarReceipt,
    DesktopSystemSnapshot,
    DesktopTargetCandidate,
    DesktopVisualGroundingRequest,
    DesktopVisualGroundingResult,
    DesktopWindowRef,
    DesktopWindowSnapshot,
    MetricAvailability,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.telemetry import TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class DesktopSidecarRuntimeError(ValueError):
    """Raised when desktop sidecar execution would violate policy or authority."""


class DesktopSidecarRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, DesktopSidecarConfig] = {}
        self._backends: dict[str, Any] = {}

    def register(self, config: DesktopSidecarConfig, *, backend: Any | None = None) -> DesktopSidecarConfig:
        self._configs[config.sidecar_id] = config
        if backend is not None:
            self._backends[config.sidecar_id] = backend
        return config

    def config(self, sidecar_id: str) -> DesktopSidecarConfig:
        try:
            return self._configs[sidecar_id]
        except KeyError as exc:
            raise DesktopSidecarRuntimeError("desktop_sidecar_not_registered") from exc

    def backend(self, sidecar_id: str) -> Any | None:
        return self._backends.get(sidecar_id)


class DesktopSidecarRuntime:
    """Mission-scoped permissioned desktop sidecar layer.

    V1 supports governed observation, monitoring snapshots, visual grounding,
    previews, and fake/injected action backends. It does not own authority and
    never captures hidden screenshots or performs ambient host control.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        registry: DesktopSidecarRegistry | None = None,
        backends: dict[str, Any] | None = None,
    ) -> None:
        self.kernel = kernel
        self.store = kernel.store
        self.registry = registry or DesktopSidecarRegistry()
        self._observations: dict[tuple[str, str], DesktopObservationResult] = {}
        self._grounding: dict[tuple[str, str], DesktopVisualGroundingResult] = {}
        self._targets: dict[tuple[str, str], DesktopTargetCandidate] = {}
        self._previews: dict[tuple[str, str], DesktopActionPreview] = {}
        self._approvals: dict[tuple[str, str], DesktopActionApproval] = {}
        self._killed: dict[tuple[str, str], DesktopKillSwitchBinding] = {}
        for key, backend in (backends or {}).items():
            self.registry._backends[key] = backend

    def register_sidecar(self, *, mission_id: str, config: DesktopSidecarConfig) -> DesktopSidecarConfig:
        self.store.load_record(mission_id)
        config = config.with_hash()
        self.registry.register(config, backend=self.registry.backend(config.sidecar_id))
        self._write_json(mission_id, "configs", config.sidecar_id, config.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_sidecar_registered",
            safe_summary="Desktop sidecar registered as permissioned local descriptor.",
            metadata={
                "sidecar_id": config.sidecar_id,
                "kind": config.kind.value,
                "maturity": config.maturity.value,
                "config_hash": config.config_hash,
                "active_mode": config.permission_policy.active_mode.value,
            },
        )
        return config

    def observe_desktop(
        self,
        *,
        mission_id: str,
        request: DesktopObservationRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopObservationResult:
        self._append_event(
            mission_id,
            event_type="desktop_observation_requested",
            safe_summary="Desktop observation requested.",
            metadata={"sidecar_id": request.sidecar_id, "request_id": request.request_id},
        )
        config = self._load_config(mission_id, request.sidecar_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_observe", sidecar_id=request.sidecar_id)
        self._assert_mission_open(mission_id, sidecar_id=request.sidecar_id)
        self._assert_not_killed(mission_id, request.sidecar_id)
        self._assert_observation_policy(config, request)
        backend = self._backend(request.sidecar_id)
        raw = _call_backend(backend, "observe", request)
        screenshot_bytes = raw.get("screenshot_bytes") or b""
        screenshot_hash = _hash_bytes(screenshot_bytes)
        regions = [region if isinstance(region, DesktopRegionRef) else DesktopRegionRef.model_validate(region) for region in (request.regions or [])]
        redaction = DesktopRedactionResult(
            sensitive_region_detected=any(region.sensitive for region in regions),
            sensitive_region_count=sum(1 for region in regions if region.sensitive),
            redacted=bool(screenshot_bytes),
            uncertain=not regions,
            safe_summary="Desktop observation redacted to hash-only screenshot evidence.",
        ).with_hash()
        screenshot = DesktopScreenshotRef(
            screenshot_hash=screenshot_hash,
            byte_count=len(screenshot_bytes),
            raw_screenshot_persisted=False,
        )
        display = DesktopDisplayRef(display_id=raw.get("display_ref") or request.display_ref).with_hash()
        app_ref = DesktopAppRef(app_ref=raw.get("app_ref") or request.app_ref).with_hash() if (raw.get("app_ref") or request.app_ref) else None
        window_ref = (
            DesktopWindowRef(window_ref=raw.get("window_ref") or request.window_ref, app_ref=(raw.get("app_ref") or request.app_ref)).with_hash()
            if (raw.get("window_ref") or request.window_ref)
            else None
        )
        receipt = self._receipt(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            operation_type="observation",
            status="observed",
            envelope=envelope,
            display_ref_hash=display.display_hash,
            window_ref_hash=window_ref.title_hash if window_ref else None,
            app_ref_hash=app_ref.app_hash if app_ref else None,
            region_ref_hashes=[region.region_hash for region in regions],
            screenshot_hash=screenshot.screenshot_hash,
            policy_hash=stable_hash(config.permission_policy.safe_model_dump()),
            sensitive_region_flags=[reason for region in regions for reason in region.sensitivity_reasons],
        )
        finalgate = self._finalgate(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            decision=DesktopFinalGateDecision.OBSERVED,
            receipt=receipt,
            passed=True,
        )
        result = DesktopObservationResult(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            status="observed",
            display_ref=display,
            window_ref=window_ref,
            app_ref=app_ref,
            region_refs=regions,
            screenshot_ref=screenshot,
            safe_text_snippet_hashes=[stable_hash(text) for text in raw.get("safe_text_snippets", [])],
            redaction_result=redaction,
            receipt=receipt,
            finalgate_certificate=finalgate,
        ).with_hash()
        self._observations[(mission_id, result.observation_id)] = result
        self._write_json(mission_id, "observations", result.observation_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_observation_completed",
            safe_summary="Desktop observation completed with hash-only screenshot evidence.",
            metadata={
                "sidecar_id": request.sidecar_id,
                "observation_hash": result.observation_hash,
                "screenshot_hash": screenshot.screenshot_hash,
                "sensitive_region_count": redaction.sensitive_region_count,
            },
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        if redaction.sensitive_region_detected:
            self._append_event(
                mission_id,
                event_type="desktop_sensitive_region_detected",
                safe_summary="Desktop observation detected sensitive region metadata.",
                metadata={"sidecar_id": request.sidecar_id, "sensitive_region_count": redaction.sensitive_region_count},
            )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_OBSERVATION_COUNT, 1.0, "Desktop observation count sample.", metadata={"sidecar_id": request.sidecar_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_RECEIPT_COMPLETENESS, 1.0, "Desktop receipt completeness sample.", metadata={"sidecar_id": request.sidecar_id})
        return result

    def capture_monitoring_snapshot(
        self,
        *,
        mission_id: str,
        sidecar_id: str,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopMonitoringResult:
        config = self._load_config(mission_id, sidecar_id)
        self._assert_authority(mission_id, envelope, required_action="desktop_monitor", sidecar_id=sidecar_id)
        self._assert_mission_open(mission_id, sidecar_id=sidecar_id)
        self._assert_not_killed(mission_id, sidecar_id)
        if DesktopControlMode.MONITOR_ONLY not in config.permission_policy.allowed_modes:
            raise DesktopSidecarRuntimeError("desktop_monitoring_not_allowed")
        backend = self._backend(sidecar_id)
        raw = _call_backend(backend, "monitor")
        system = DesktopSystemSnapshot(
            platform_system=redact_operator_text(str(raw.get("platform_system") or platform.system() or "UNKNOWN")),
            current_session_ref_hash=stable_hash(os.environ.get("USERNAME") or os.environ.get("USER") or "local-session"),
            display_count=int(raw.get("display_count") or 1),
            active_window_hash=stable_hash(raw.get("active_window_title")) if raw.get("active_window_title") else None,
        ).with_hash()
        processes = [
            DesktopProcessSnapshot(
                process_id_hash=stable_hash(str(item.get("pid", "unknown"))),
                name_hash=stable_hash(item.get("name", "unknown")),
                cpu_percent=_metric(item.get("cpu_percent"), "%"),
                memory_mb=_metric(item.get("memory_mb"), "mb"),
            )
            for item in raw.get("processes", [])
        ]
        windows = [
            DesktopWindowSnapshot(window_ref_hash=stable_hash(title), active=title == raw.get("active_window_title"))
            for title in raw.get("visible_windows", [])
        ]
        apps = [DesktopAppSnapshot(app_ref_hash=stable_hash(app)) for app in raw.get("running_apps", [])]
        hardware = DesktopHardwareMetricSnapshot(
            cpu_percent=_metric(raw.get("cpu_percent"), "%"),
            ram_used_mb=_metric(raw.get("ram_used_mb"), "mb"),
            disk_used_percent=_metric(raw.get("disk_used_percent"), "%"),
            network_rx_kbps=_metric(raw.get("network_rx_kbps"), "kbps"),
            battery_percent=_metric(raw.get("battery_percent"), "%", unavailable_status=MetricAvailability.UNKNOWN),
            gpu_percent=_metric(raw.get("gpu_percent"), "%", unavailable_status=MetricAvailability.UNKNOWN),
        )
        sensors = DesktopSensorSnapshot(
            temperature_c=_metric(raw.get("temperature_c"), "c", unavailable_status=MetricAvailability.UNKNOWN),
            fan_rpm=_metric(raw.get("fan_rpm"), "rpm", unavailable_status=MetricAvailability.UNKNOWN),
        )
        clock = DesktopClockSnapshot(system_time_hash=stable_hash(datetime.now(UTC).isoformat()))
        receipt = DesktopMonitoringReceipt(
            sidecar_id=sidecar_id,
            mission_id=mission_id,
            operation_type="monitoring",
            status="observed",
            authority_envelope_ref=envelope.id if envelope else None,
            policy_hash=stable_hash(config.permission_policy.monitoring_policy.safe_model_dump()),
        ).with_hash()
        result = DesktopMonitoringResult(
            sidecar_id=sidecar_id,
            mission_id=mission_id,
            system_snapshot=system,
            processes=processes,
            windows=windows,
            apps=apps,
            hardware_metrics=hardware,
            sensor_snapshot=sensors,
            clock_snapshot=clock,
            background_activity={
                "visible_window_count": len(windows),
                "running_app_count": len(apps),
                "process_count": len(processes),
            },
            monitoring_receipt=receipt,
        ).with_hash()
        self._write_json(mission_id, "monitoring", result.monitoring_result_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_observation_completed",
            safe_summary="Desktop monitoring snapshot captured with safe local metric summaries.",
            metadata={"sidecar_id": sidecar_id, "monitoring_hash": result.result_hash},
            receipt_refs=[receipt.receipt_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_OBSERVATION_COUNT, 1.0, "Desktop monitoring observation count sample.", metadata={"sidecar_id": sidecar_id})
        return result

    def ground_visual_target(self, *, mission_id: str, request: DesktopVisualGroundingRequest) -> DesktopVisualGroundingResult:
        self._append_event(
            mission_id,
            event_type="desktop_grounding_requested",
            safe_summary="Desktop visual grounding requested.",
            metadata={"sidecar_id": request.sidecar_id, "observation_id": request.observation_id},
        )
        config = self._load_config(mission_id, request.sidecar_id)
        if not config.capability_profile.supports_visual_grounding:
            raise DesktopSidecarRuntimeError("desktop_grounding_not_supported")
        observation = self._load_observation(mission_id, request.observation_id)
        candidates = _candidates_from_observation(observation, request)
        status = "grounded"
        uncertainty_flags: list[str] = []
        if not candidates or max(candidate.confidence_score for candidate in candidates) < request.ambiguity_threshold:
            status = "needs_operator_checkpoint"
            uncertainty_flags.append("ambiguous_target")
        receipt = self._receipt(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            operation_type="grounding",
            status=status,
            envelope=None,
            target_candidate_refs=[candidate.target_id for candidate in candidates],
            policy_hash=stable_hash({"ambiguity_threshold": request.ambiguity_threshold}),
            sensitive_region_flags=[reason for candidate in candidates for reason in candidate.region_ref.sensitivity_reasons],
        )
        finalgate = self._finalgate(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            decision=DesktopFinalGateDecision.GROUNDED if status == "grounded" else DesktopFinalGateDecision.NEEDS_APPROVAL,
            receipt=receipt,
            passed=True,
        )
        result = DesktopVisualGroundingResult(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            observation_id=request.observation_id,
            status=status,
            target_candidates=candidates,
            uncertainty_flags=uncertainty_flags,
            grounding_receipt=receipt,
            finalgate_certificate=finalgate,
        ).with_hash()
        self._grounding[(mission_id, result.grounding_id)] = result
        for candidate in candidates:
            self._targets[(mission_id, candidate.target_id)] = candidate
        self._write_json(mission_id, "grounding", result.grounding_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_grounding_completed" if status == "grounded" else "desktop_grounding_failed",
            safe_summary=f"Desktop visual grounding {status}.",
            metadata={"sidecar_id": request.sidecar_id, "grounding_hash": result.grounding_hash, "candidate_count": len(candidates)},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.DESKTOP_GROUNDING_SUCCESS_RATE,
            1.0 if status == "grounded" else 0.0,
            "Desktop grounding success sample.",
            metadata={"sidecar_id": request.sidecar_id},
        )
        if status != "grounded":
            self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_GROUNDING_AMBIGUITY_RATE, 1.0, "Desktop grounding ambiguity sample.", metadata={"sidecar_id": request.sidecar_id})
        return result

    def preview_action(self, *, mission_id: str, request: DesktopActionRequest) -> DesktopActionPreview:
        config = self._load_config(mission_id, request.sidecar_id)
        self._assert_action_policy(config, request)
        target = self._load_target(mission_id, request.target_candidate_id) if request.target_candidate_id else None
        proposal = DesktopActionProposal(
            sidecar_id=request.sidecar_id,
            action_kind=request.action_kind,
            target_candidate_id=request.target_candidate_id,
            app_ref_hash=stable_hash(request.app_ref) if request.app_ref else None,
            window_ref_hash=stable_hash(request.window_ref) if request.window_ref else None,
            safe_summary=f"Desktop {request.action_kind.value} proposed for operator-visible approval.",
            evidence_refs=list(request.evidence_refs),
        ).with_hash()
        preview = DesktopActionPreview(sidecar_id=request.sidecar_id, action_request=request, action_proposal=proposal).with_hash()
        self._previews[(mission_id, preview.preview_id)] = preview
        self._write_json(mission_id, "previews", preview.preview_id, preview.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_action_preview_created",
            safe_summary="Desktop action preview created; no action executed.",
            metadata={
                "sidecar_id": request.sidecar_id,
                "preview_ref_hash": stable_hash(preview.preview_id),
                "preview_hash": preview.preview_hash,
            },
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_ACTION_PREVIEW_COUNT, 1.0, "Desktop action preview count sample.", metadata={"sidecar_id": request.sidecar_id})
        return preview

    def approve_action(self, *, mission_id: str, approval: DesktopActionApproval) -> DesktopActionApproval:
        self.store.load_record(mission_id)
        approval = approval.with_hash()
        self._approvals[(mission_id, approval.approval_id)] = approval
        self._write_json(mission_id, "approvals", approval.approval_id, approval.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_action_approved",
            safe_summary="Operator desktop action approval recorded.",
            metadata={"sidecar_id": approval.sidecar_id, "preview_ref_hash": stable_hash(approval.preview_id), "approval_hash": approval.approval_hash},
        )
        return approval

    def execute_action(
        self,
        *,
        mission_id: str,
        request: DesktopActionRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> DesktopActionResult:
        config = self._load_config(mission_id, request.sidecar_id)
        self._append_event(
            mission_id,
            event_type="desktop_action_started",
            safe_summary="Desktop action execution requested.",
            metadata={"sidecar_id": request.sidecar_id},
        )
        self._assert_authority(mission_id, envelope, required_action="desktop_action", sidecar_id=request.sidecar_id)
        self._assert_mission_open(mission_id, sidecar_id=request.sidecar_id)
        self._assert_not_killed(mission_id, request.sidecar_id)
        self._assert_action_policy(config, request)
        self._assert_action_scope(config, request)
        self._assert_approval(mission_id, config, request)
        target = self._load_target(mission_id, request.target_candidate_id) if request.target_candidate_id else None
        if target and target.sensitive:
            return self._blocked_action_result(
                mission_id,
                request,
                reason="sensitive_region_blocked",
                decision=DesktopFinalGateDecision.SENSITIVE_REGION_BLOCKED,
                metric_kind=TelemetryMetricKind.DESKTOP_SENSITIVE_REGION_BLOCK_COUNT,
            )
        backend = self._backend(request.sidecar_id)
        raw = _call_backend(backend, "perform_action", request)
        before_after = DesktopBeforeAfterEvidence(
            before_hash=str(raw.get("before_hash") or stable_hash("before")),
            after_hash=str(raw.get("after_hash") or stable_hash("after")),
            safe_summary=redact_operator_text(str(raw.get("safe_summary") or "Desktop action completed.")),
        ).with_hash()
        receipt = self._receipt(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            operation_type=f"action:{request.action_kind.value}",
            status="completed",
            envelope=envelope,
            app_ref_hash=stable_hash(request.app_ref) if request.app_ref else None,
            window_ref_hash=stable_hash(request.window_ref) if request.window_ref else None,
            target_candidate_refs=[request.target_candidate_id] if request.target_candidate_id else [],
            policy_hash=stable_hash(config.action_policy.safe_model_dump()),
            approval_ref=request.approval_id,
            before_after_hash=before_after.evidence_hash,
            sensitive_region_flags=[],
        )
        finalgate = self._finalgate(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            decision=DesktopFinalGateDecision.OBSERVED,
            receipt=receipt,
            passed=True,
        )
        result = DesktopActionResult(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            action_kind=request.action_kind,
            status=str(raw.get("status") or "completed"),
            before_after_evidence=before_after,
            receipt=receipt,
            finalgate_certificate=finalgate,
            safe_summary=redact_operator_text(str(raw.get("safe_summary") or "Desktop action completed through injected backend.")),
        ).with_hash()
        self._write_json(mission_id, "before_after", before_after.evidence_id, before_after.safe_model_dump())
        self._write_json(mission_id, "action_results", result.action_result_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_action_completed",
            safe_summary="Desktop injected action completed with before/after evidence.",
            metadata={"sidecar_id": request.sidecar_id, "result_hash": result.result_hash},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_ACTION_SUCCESS_RATE, 1.0, "Desktop action success sample.", metadata={"sidecar_id": request.sidecar_id})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_RECEIPT_COMPLETENESS, 1.0, "Desktop receipt completeness sample.", metadata={"sidecar_id": request.sidecar_id})
        return result

    def kill_sidecar(self, *, mission_id: str, sidecar_id: str, reason: str) -> DesktopKillSwitchBinding:
        binding = DesktopKillSwitchBinding(sidecar_id=sidecar_id, mission_id=mission_id, killed=True, reason_hash=stable_hash(reason))
        self._killed[(mission_id, sidecar_id)] = binding
        self._write_json(mission_id, "kill", sidecar_id, binding.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_kill_switch_triggered",
            safe_summary="Desktop sidecar kill switch triggered.",
            metadata={"sidecar_id": sidecar_id, "reason_hash": binding.reason_hash},
        )
        return binding

    def _blocked_action_result(
        self,
        mission_id: str,
        request: DesktopActionRequest,
        *,
        reason: str,
        decision: DesktopFinalGateDecision,
        metric_kind: TelemetryMetricKind,
    ) -> DesktopActionResult:
        receipt = self._receipt(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            operation_type=f"action:{request.action_kind.value}",
            status="blocked",
            envelope=None,
            policy_hash=stable_hash({"blocked_reason": reason}),
            target_candidate_refs=[request.target_candidate_id] if request.target_candidate_id else [],
            sensitive_region_flags=[reason],
        )
        finalgate = self._finalgate(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            decision=decision,
            receipt=receipt,
            passed=True,
        )
        result = DesktopActionResult(
            sidecar_id=request.sidecar_id,
            mission_id=mission_id,
            action_kind=request.action_kind,
            status="blocked",
            blocked_reason=reason,
            receipt=receipt,
            finalgate_certificate=finalgate,
            safe_summary=f"Desktop action blocked: {reason}.",
        ).with_hash()
        self._write_json(mission_id, "action_results", result.action_result_id, result.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="desktop_action_blocked",
            safe_summary=result.safe_summary,
            metadata={"sidecar_id": request.sidecar_id, "reason_hash": stable_hash(reason)},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(mission_id, metric_kind, 1.0, "Desktop action block sample.", metadata={"sidecar_id": request.sidecar_id, "reason_hash": stable_hash(reason)})
        self._record_metric(mission_id, TelemetryMetricKind.DESKTOP_ACTION_BLOCK_COUNT, 1.0, "Desktop action block count sample.", metadata={"sidecar_id": request.sidecar_id})
        return result

    def _assert_authority(
        self,
        mission_id: str,
        envelope: MissionAuthorityEnvelope | None,
        *,
        required_action: str,
        sidecar_id: str,
    ) -> None:
        if envelope is None:
            raise DesktopSidecarRuntimeError("desktop_action_authority_missing" if required_action == "desktop_action" else "desktop_authority_missing")
        if envelope.id != mission_id:
            raise DesktopSidecarRuntimeError("mission_authority_envelope_mismatch")
        if getattr(envelope, "revoked_at", None) is not None:
            self._append_event(mission_id, event_type="desktop_revocation_detected", safe_summary="Desktop sidecar blocked by revoked authority.", metadata={"sidecar_id": sidecar_id})
            raise DesktopSidecarRuntimeError("desktop_authority_revoked")
        if envelope.resolved_expires_at() <= datetime.now(UTC):
            raise DesktopSidecarRuntimeError("desktop_authority_expired")
        allowed = set(getattr(envelope, "allowed_actions", []) or [])
        if required_action not in allowed and "desktop_action" not in allowed:
            raise DesktopSidecarRuntimeError("desktop_action_not_allowed_by_envelope")
        tools = set(getattr(envelope, "allowed_tools", []) or [])
        if "desktop_sidecar" not in tools and sidecar_id not in tools:
            raise DesktopSidecarRuntimeError("desktop_tool_not_allowed_by_envelope")

    def _assert_mission_open(self, mission_id: str, *, sidecar_id: str) -> None:
        reason = self.kernel.terminal_block_reason(mission_id)
        if reason:
            if reason.endswith(":killed"):
                self._append_event(mission_id, event_type="desktop_kill_switch_triggered", safe_summary="Desktop sidecar blocked by mission kill switch.", metadata={"sidecar_id": sidecar_id})
            raise DesktopSidecarRuntimeError(reason)

    def _assert_not_killed(self, mission_id: str, sidecar_id: str) -> None:
        if (mission_id, sidecar_id) in self._killed:
            raise DesktopSidecarRuntimeError("desktop_sidecar_killed")
        path = self._path(mission_id, "kill", sidecar_id)
        if path.exists():
            binding = DesktopKillSwitchBinding.model_validate_json(path.read_text(encoding="utf-8"))
            if binding.killed:
                self._killed[(mission_id, sidecar_id)] = binding
                raise DesktopSidecarRuntimeError("desktop_sidecar_killed")

    def _assert_observation_policy(self, config: DesktopSidecarConfig, request: DesktopObservationRequest) -> None:
        if not config.permission_policy.operator_visible or not request.operator_visible or request.ambient_loop:
            raise DesktopSidecarRuntimeError("desktop_hidden_or_ambient_capture_blocked")
        if not config.capability_profile.supports_observation:
            raise DesktopSidecarRuntimeError("desktop_observation_not_supported")
        self._assert_app_window_display_scope(config.permission_policy, request.app_ref, request.window_ref, request.display_ref)
        for region in request.regions:
            if region.label in set(config.permission_policy.blocked_region_labels):
                raise DesktopSidecarRuntimeError("desktop_observation_blocked_region")

    def _assert_action_policy(self, config: DesktopSidecarConfig, request: DesktopActionRequest) -> None:
        if request.action_kind not in config.action_policy.allowed_action_kinds:
            raise DesktopSidecarRuntimeError("desktop_action_not_allowed_by_policy")
        if config.permission_policy.active_mode in {DesktopControlMode.OBSERVE_ONLY, DesktopControlMode.MONITOR_ONLY, DesktopControlMode.ASSISTED_OPERATOR}:
            raise DesktopSidecarRuntimeError("desktop_action_mode_not_allowed")

    def _assert_action_scope(self, config: DesktopSidecarConfig, request: DesktopActionRequest) -> None:
        self._assert_app_window_display_scope(config.permission_policy, request.app_ref, request.window_ref, None)

    def _assert_app_window_display_scope(
        self,
        policy: DesktopPermissionPolicy,
        app_ref: str | None,
        window_ref: str | None,
        display_ref: str | None,
    ) -> None:
        if app_ref and app_ref in set(policy.blocked_apps):
            raise DesktopSidecarRuntimeError("desktop_observation_blocked_app")
        if app_ref and policy.allowed_apps and app_ref not in set(policy.allowed_apps):
            raise DesktopSidecarRuntimeError("desktop_app_not_allowed")
        if window_ref and window_ref in set(policy.blocked_windows):
            raise DesktopSidecarRuntimeError("desktop_observation_blocked_window")
        if window_ref and policy.allowed_windows and window_ref not in set(policy.allowed_windows):
            raise DesktopSidecarRuntimeError("desktop_window_not_allowed")
        if display_ref and policy.allowed_displays and display_ref not in set(policy.allowed_displays):
            raise DesktopSidecarRuntimeError("desktop_display_not_allowed")

    def _assert_approval(self, mission_id: str, config: DesktopSidecarConfig, request: DesktopActionRequest) -> None:
        if request.requested_by not in {"operator", "operator_policy", "manual_operator"}:
            raise DesktopSidecarRuntimeError("operator_approval_required")
        if not config.action_policy.approval_required_for_each_action and config.permission_policy.active_mode is DesktopControlMode.DELEGATED_SESSION_OPERATOR:
            return
        if not request.approval_id:
            self._append_event(mission_id, event_type="desktop_action_approval_required", safe_summary="Desktop action requires operator approval.", metadata={"sidecar_id": request.sidecar_id})
            raise DesktopSidecarRuntimeError("operator_approval_required")
        approval = self._approvals.get((mission_id, request.approval_id)) or self._load_approval(mission_id, request.approval_id)
        preview = self._previews.get((mission_id, approval.preview_id)) if approval else None
        if approval is None or not approval.verify_hash() or not approval.approved:
            raise DesktopSidecarRuntimeError("operator_approval_required")
        if preview is not None and preview.action_request.request_id != request.request_id:
            raise DesktopSidecarRuntimeError("operator_approval_required")

    def _receipt(
        self,
        *,
        sidecar_id: str,
        mission_id: str,
        operation_type: str,
        status: str,
        envelope: MissionAuthorityEnvelope | None,
        display_ref_hash: str | None = None,
        window_ref_hash: str | None = None,
        app_ref_hash: str | None = None,
        region_ref_hashes: list[str] | None = None,
        screenshot_hash: str | None = None,
        target_candidate_refs: list[str] | None = None,
        policy_hash: str | None = None,
        approval_ref: str | None = None,
        before_after_hash: str | None = None,
        sensitive_region_flags: list[str] | None = None,
    ) -> DesktopSidecarReceipt:
        return DesktopSidecarReceipt(
            sidecar_id=sidecar_id,
            mission_id=mission_id,
            operation_type=operation_type,
            status=status,
            authority_envelope_ref=envelope.id if envelope else None,
            display_ref_hash=display_ref_hash,
            window_ref_hash=window_ref_hash,
            app_ref_hash=app_ref_hash,
            region_ref_hashes=region_ref_hashes or [],
            screenshot_hash=screenshot_hash,
            target_candidate_refs=target_candidate_refs or [],
            policy_hash=policy_hash,
            approval_ref=approval_ref,
            before_after_hash=before_after_hash,
            sensitive_region_flags=sensitive_region_flags or [],
        ).with_hash()

    def _finalgate(
        self,
        *,
        sidecar_id: str,
        mission_id: str,
        decision: DesktopFinalGateDecision,
        receipt: DesktopSidecarReceipt,
        passed: bool,
        failures: list[str] | None = None,
    ) -> DesktopSidecarFinalGateCertificate:
        return DesktopSidecarFinalGateCertificate(
            sidecar_id=sidecar_id,
            mission_id=mission_id,
            decision=decision,
            passed=passed,
            receipt_ref=receipt.receipt_id,
            failures=failures or [],
        )

    def _load_config(self, mission_id: str, sidecar_id: str) -> DesktopSidecarConfig:
        try:
            return self.registry.config(sidecar_id)
        except DesktopSidecarRuntimeError:
            path = self._path(mission_id, "configs", sidecar_id)
            if not path.exists():
                raise
            config = DesktopSidecarConfig.model_validate_json(path.read_text(encoding="utf-8"))
            if not config.verify_hash():
                raise DesktopSidecarRuntimeError("desktop_sidecar_config_hash_mismatch")
            self.registry.register(config)
            return config

    def _load_observation(self, mission_id: str, observation_id: str) -> DesktopObservationResult:
        cached = self._observations.get((mission_id, observation_id))
        if cached:
            return cached
        for path in (self.store.mission_dir(mission_id) / "desktop_sidecar" / "observations").glob("*.json"):
            result = DesktopObservationResult.model_validate_json(path.read_text(encoding="utf-8"))
            if result.observation_id == observation_id:
                self._observations[(mission_id, observation_id)] = result
                return result
        raise DesktopSidecarRuntimeError("desktop_observation_not_found")

    def _load_target(self, mission_id: str, target_candidate_id: str | None) -> DesktopTargetCandidate | None:
        if target_candidate_id is None:
            return None
        cached = self._targets.get((mission_id, target_candidate_id))
        if cached:
            return cached
        for grounding_path in (self.store.mission_dir(mission_id) / "desktop_sidecar" / "grounding").glob("*.json"):
            result = DesktopVisualGroundingResult.model_validate_json(grounding_path.read_text(encoding="utf-8"))
            for candidate in result.target_candidates:
                self._targets[(mission_id, candidate.target_id)] = candidate
                if candidate.target_id == target_candidate_id:
                    return candidate
        raise DesktopSidecarRuntimeError("desktop_target_not_found")

    def _load_approval(self, mission_id: str, approval_id: str) -> DesktopActionApproval | None:
        path = self._path(mission_id, "approvals", approval_id)
        if not path.exists():
            return None
        approval = DesktopActionApproval.model_validate_json(path.read_text(encoding="utf-8"))
        self._approvals[(mission_id, approval.approval_id)] = approval
        return approval

    def _backend(self, sidecar_id: str) -> Any:
        backend = self.registry.backend(sidecar_id)
        if backend is None:
            raise DesktopSidecarRuntimeError("desktop_sidecar_backend_missing")
        return backend

    def _write_json(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self.store.atomic_write_json(self._path(mission_id, category, name), payload)

    def _path(self, mission_id: str, category: str, name: str) -> Path:
        return self.store.mission_dir(mission_id, create=True) / "desktop_sidecar" / category / f"{stable_hash(name)[:24]}.json"

    def _append_event(
        self,
        mission_id: str,
        *,
        event_type: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ):
        return self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=[ref for ref in (receipt_refs or []) if ref],
            finalgate_certificate_refs=[ref for ref in (finalgate_certificate_refs or []) if ref],
        )

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: float,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = getattr(self.store, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.DESKTOP_SIDECAR,
                metric_kind=metric_kind,
                value=value,
                unit="count",
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )


def _call_backend(backend: Any, method: str, *args: Any) -> dict[str, Any]:
    fn = getattr(backend, method, None)
    if fn is None:
        return {}
    result = fn(*args)
    return dict(result or {})


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest() if value else stable_hash("desktop-empty-screenshot")


def _metric(value: Any, unit: str, *, unavailable_status: MetricAvailability = MetricAvailability.UNKNOWN) -> DesktopMetricValue:
    if value is None:
        return DesktopMetricValue(status=unavailable_status, unit=unit, safe_summary=f"{unit} metric unavailable.")
    try:
        return DesktopMetricValue(status=MetricAvailability.AVAILABLE, value=float(value), unit=unit, safe_summary="Metric available.")
    except (TypeError, ValueError):
        return DesktopMetricValue(status=MetricAvailability.UNKNOWN, unit=unit, safe_summary="Metric unknown.")


def _candidates_from_observation(
    observation: DesktopObservationResult,
    request: DesktopVisualGroundingRequest,
) -> list[DesktopTargetCandidate]:
    if not observation.region_refs:
        return []
    ambiguous = "ambiguous" in request.target_description.lower()
    confidence = 0.6 if ambiguous else 0.9
    candidates = []
    for region in observation.region_refs:
        candidates.append(
            DesktopTargetCandidate(
                observation_id=observation.observation_id,
                target_ref_hash=stable_hash({"observation_id": observation.observation_id, "region_hash": region.region_hash, "target": request.target_description}),
                region_ref=region,
                confidence_score=confidence,
                evidence_refs=list(request.evidence_refs),
                ambiguous=ambiguous,
                sensitive=region.sensitive,
            )
        )
    return candidates
