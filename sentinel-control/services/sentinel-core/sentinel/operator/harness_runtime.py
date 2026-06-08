from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.harness_models import (
    AmplificationHarnessConfig,
    AmplificationSession,
    AnalysisKernelConfig,
    AnalysisKernelResult,
    AnalysisKernelSession,
    ContentAddressedArtifact,
    HarnessCompressionPolicy,
    HarnessConflictRecord,
    HarnessContextPack,
    HarnessMergeDecision,
    HarnessWorkerRequest,
    HarnessWorkerResult,
    HashAnchoredEditVerification,
    HashAnchoredPatch,
    MinimizedToolResult,
    ToolOutputEnvelope,
    harness_utc_now,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.telemetry import (
    TelemetryDomain,
    TelemetryMetricKind,
    TelemetryMetricSample,
    TelemetrySourceSurface,
)


class HarnessRuntimeError(RuntimeError):
    pass


class AmplificationHarnessRuntime:
    """Mission-scoped model amplification over the existing Sentinel spine.

    The harness stores compact hashes, refs, safe summaries, and replayable
    decisions. It never executes actions and never creates authority; any
    amplified plan that needs real effects must be routed through MissionKernel,
    WorkerFleetRuntime, PowerRuntime, or AgentRuntime bridge contracts.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        config: AmplificationHarnessConfig | None = None,
        worker_fleet_runtime: object | None = None,
        memory_adapter: object | None = None,
    ) -> None:
        self.kernel = kernel
        self.config = config or AmplificationHarnessConfig()
        self.worker_fleet_runtime = worker_fleet_runtime
        self.memory_adapter = memory_adapter
        self._artifact_contents: dict[tuple[str, str], str] = {}

    def start_session(
        self,
        *,
        mission_id: str,
        envelope: MissionAuthorityEnvelope,
        provider_id: str | None = None,
        backend_id: str | None = None,
        model_id: str | None = None,
        requested_provider_id: str | None = None,
        requested_backend_id: str | None = None,
        requested_model_id: str | None = None,
        memory_context_refs: list[str] | None = None,
        safe_summary: str = "Amplification harness session started.",
    ) -> AmplificationSession:
        self._assert_supported_mission(mission_id)
        self._assert_envelope_matches(mission_id, envelope)
        self._assert_model_contract_unchanged(
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
            requested_provider_id=requested_provider_id,
            requested_backend_id=requested_backend_id,
            requested_model_id=requested_model_id,
        )
        session = AmplificationSession(
            mission_id=mission_id,
            parent_envelope_id=envelope.id,
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
            memory_context_refs=memory_context_refs or [],
            safe_summary=safe_summary,
        ).with_hash()
        self._persist_session(session)
        self._append_event(
            mission_id,
            event_type="harness_session_started",
            safe_summary="Amplification harness session started.",
            metadata={
                "session_id": session.session_id,
                "provider_id_hash": stable_hash(provider_id) if provider_id else None,
                "backend_id_hash": stable_hash(backend_id) if backend_id else None,
                "model_id_hash": stable_hash(model_id) if model_id else None,
            },
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.HARNESS_SCHEMA_VALID_RATE,
            value=1.0,
            safe_summary="Harness session schema validation passed.",
            metadata={"session_id": session.session_id},
        )
        return session

    def complete_session(self, *, mission_id: str, session_id: str, safe_summary: str) -> AmplificationSession:
        session = self._load_session(mission_id, session_id)
        session = session.model_copy(
            update={
                "status": "completed",
                "safe_summary": redact_operator_text(safe_summary),
                "updated_at": harness_utc_now(),
                "session_hash": "",
            }
        ).with_hash()
        self._persist_session(session)
        self._append_event(
            mission_id,
            event_type="harness_session_completed",
            safe_summary="Amplification harness session completed.",
            metadata={"session_id": session.session_id},
        )
        return session

    def record_artifact(
        self,
        *,
        mission_id: str,
        session_id: str,
        logical_path: str,
        content: str | bytes,
        media_type: str = "text/plain",
        metadata: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> ContentAddressedArtifact:
        self._load_session(mission_id, session_id)
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
            content_text = content
        else:
            content_bytes = content
            content_text = content.decode("utf-8", errors="replace")
        artifact = ContentAddressedArtifact.from_bytes(
            mission_id=mission_id,
            logical_path=logical_path,
            content=content_bytes,
            media_type=media_type,
            metadata=metadata or {},
            evidence_refs=evidence_refs or [],
        )
        self._artifact_contents[(mission_id, artifact.artifact_ref)] = content_text
        self._write_json(
            self._entity_path(mission_id, "artifacts", session_id, artifact.artifact_ref),
            artifact.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_artifact_read",
            safe_summary="Harness recorded content-addressed artifact preview.",
            metadata={
                "session_id": session_id,
                "artifact_ref": artifact.artifact_ref,
                "logical_path": artifact.logical_path,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            },
            receipt_refs=[],
            finalgate_certificate_refs=[],
            memory_feedback_refs=[],
        )
        return artifact

    def verify_edit(
        self,
        *,
        mission_id: str,
        session_id: str,
        patch: HashAnchoredPatch,
    ) -> HashAnchoredEditVerification:
        self._load_session(mission_id, session_id)
        artifact = self._load_artifact(mission_id, patch.artifact_ref)
        self._write_json(
            self._entity_path(mission_id, "edit_proposals", session_id, patch.edit_id),
            patch.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_edit_proposed",
            safe_summary="Harness hash-anchored edit proposed.",
            metadata={"session_id": session_id, "edit_id": patch.edit_id, "artifact_ref": patch.artifact_ref},
            receipt_refs=[],
            finalgate_certificate_refs=[],
            memory_feedback_refs=[],
        )
        if artifact.sha256 != patch.base_sha256:
            verification = HashAnchoredEditVerification(
                mission_id=mission_id,
                session_id=session_id,
                edit_id=patch.edit_id,
                artifact_ref=patch.artifact_ref,
                status="rejected",
                before_sha256=artifact.sha256,
                expected_sha256=patch.expected_sha256,
                reject_reason="base_hash_mismatch",
                evidence_refs=patch.evidence_refs,
            ).with_hash()
            self._persist_edit_verification(verification)
            self._append_event(
                mission_id,
                event_type="harness_edit_rejected",
                safe_summary="Harness hash-anchored edit rejected.",
                metadata={"session_id": session_id, "edit_id": patch.edit_id, "reason": verification.reject_reason},
            )
            return verification
        after_sha256 = stable_hash(patch.replacement_text)
        if after_sha256 != patch.expected_sha256:
            verification = HashAnchoredEditVerification(
                mission_id=mission_id,
                session_id=session_id,
                edit_id=patch.edit_id,
                artifact_ref=patch.artifact_ref,
                status="rejected",
                before_sha256=artifact.sha256,
                expected_sha256=patch.expected_sha256,
                after_sha256=after_sha256,
                reject_reason="after_hash_mismatch",
                evidence_refs=patch.evidence_refs,
            ).with_hash()
            self._persist_edit_verification(verification)
            self._append_event(
                mission_id,
                event_type="harness_edit_rejected",
                safe_summary="Harness hash-anchored edit rejected.",
                metadata={"session_id": session_id, "edit_id": patch.edit_id, "reason": verification.reject_reason},
            )
            return verification
        self._artifact_contents[(mission_id, patch.artifact_ref)] = patch.replacement_text
        verification = HashAnchoredEditVerification(
            mission_id=mission_id,
            session_id=session_id,
            edit_id=patch.edit_id,
            artifact_ref=patch.artifact_ref,
            status="verified",
            before_sha256=artifact.sha256,
            expected_sha256=patch.expected_sha256,
            after_sha256=after_sha256,
            evidence_refs=patch.evidence_refs,
        ).with_hash()
        self._persist_edit_verification(verification)
        self._append_event(
            mission_id,
            event_type="harness_edit_verified",
            safe_summary="Harness hash-anchored edit verified.",
            metadata={"session_id": session_id, "edit_id": patch.edit_id, "artifact_ref": patch.artifact_ref},
            receipt_refs=[],
            finalgate_certificate_refs=[],
            memory_feedback_refs=[],
        )
        return verification

    def start_analysis_kernel(
        self,
        *,
        mission_id: str,
        session_id: str,
        config: AnalysisKernelConfig,
    ) -> AnalysisKernelSession:
        self._load_session(mission_id, session_id)
        if config.requests_ambient_access:
            self._append_event(
                mission_id,
                event_type="harness_kernel_failed",
                safe_summary="Harness analysis kernel rejected ambient execution request.",
                metadata={"session_id": session_id, "kernel_name": config.kernel_name},
            )
            raise ValueError("analysis kernel cannot access ambient execution")
        session = AnalysisKernelSession(
            mission_id=mission_id,
            session_id=session_id,
            kernel_name=config.kernel_name,
            input_refs=config.input_refs,
        ).with_hash()
        self._write_json(
            self._entity_path(mission_id, "kernels", session_id, session.kernel_session_id),
            session.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_kernel_started",
            safe_summary="Harness analysis kernel started.",
            metadata={"session_id": session_id, "kernel_session_id": session.kernel_session_id},
        )
        return session

    def run_analysis_kernel(
        self,
        *,
        mission_id: str,
        session_id: str,
        config: AnalysisKernelConfig,
        safe_summary: str,
        output: dict[str, Any],
    ) -> AnalysisKernelResult:
        kernel = self.start_analysis_kernel(mission_id=mission_id, session_id=session_id, config=config)
        result = AnalysisKernelResult(
            mission_id=mission_id,
            session_id=session_id,
            kernel_session_id=kernel.kernel_session_id,
            status="completed",
            safe_summary=safe_summary,
            output=output,
        ).with_hash()
        self._write_json(
            self._entity_path(mission_id, "kernel_results", session_id, result.kernel_result_id),
            result.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_kernel_completed",
            safe_summary="Harness analysis kernel completed.",
            metadata={"session_id": session_id, "kernel_result_id": result.kernel_result_id},
        )
        return result

    def minimize_tool_output(
        self,
        *,
        mission_id: str,
        session_id: str,
        envelope: ToolOutputEnvelope,
    ) -> MinimizedToolResult:
        self._load_session(mission_id, session_id)
        result = MinimizedToolResult(
            tool_result_ref=envelope.tool_result_ref,
            mission_id=mission_id,
            tool_name=envelope.tool_name,
            safe_summary=envelope.safe_summary,
            raw_output_bytes=envelope.raw_output_bytes,
            minimized_output=envelope.minimized_output,
            evidence_refs=envelope.evidence_refs,
            receipt_refs=envelope.receipt_refs,
            finalgate_certificate_refs=envelope.finalgate_certificate_refs,
            memory_feedback_refs=envelope.memory_feedback_refs,
            raw_output_persisted=False,
            persisted_output_bytes=len(json.dumps(envelope.minimized_output, sort_keys=True, default=str).encode("utf-8")),
        ).with_hash()
        self._write_json(
            self._entity_path(mission_id, "tool_results", session_id, result.tool_result_ref),
            result.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_tool_output_minimized",
            safe_summary="Harness minimized structured tool output.",
            metadata={"session_id": session_id, "tool_result_ref": result.tool_result_ref, "tool_name": result.tool_name},
            receipt_refs=result.receipt_refs,
            finalgate_certificate_refs=result.finalgate_certificate_refs,
            memory_feedback_refs=result.memory_feedback_refs,
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.HARNESS_TOOL_OUTPUT_BYTES_INPUT,
            value=result.raw_output_bytes,
            unit="bytes",
            safe_summary="Harness tool output input bytes sample.",
            metadata={"session_id": session_id, "tool_result_ref": result.tool_result_ref},
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.HARNESS_TOOL_OUTPUT_BYTES_PERSISTED,
            value=result.persisted_output_bytes,
            unit="bytes",
            safe_summary="Harness minimized tool output persisted bytes sample.",
            metadata={"session_id": session_id, "tool_result_ref": result.tool_result_ref},
        )
        return result

    def build_context_pack(
        self,
        *,
        mission_id: str,
        session_id: str,
        safe_goal: str,
        tool_results: list[MinimizedToolResult],
        required_refs: list[str] | None = None,
        compression_policy: HarnessCompressionPolicy | None = None,
    ) -> HarnessContextPack:
        self._load_session(mission_id, session_id)
        policy = compression_policy or HarnessCompressionPolicy(max_items=self.config.max_context_items)
        selected = list(tool_results[: policy.max_items])
        safe_context_items: list[str] = []
        compressed = len(tool_results) > len(selected)
        tokens_saved = 0
        for result in selected:
            item = result.safe_summary
            if len(item) > policy.max_summary_chars:
                tokens_saved += max(0, len(item) - policy.max_summary_chars) // 4
                item = item[: policy.max_summary_chars]
                compressed = True
            safe_context_items.append(item)
        evidence_refs = _dedupe(ref for result in selected for ref in result.evidence_refs)
        receipt_refs = _dedupe(ref for result in selected for ref in result.receipt_refs)
        finalgate_refs = _dedupe(ref for result in selected for ref in result.finalgate_certificate_refs)
        memory_refs = _dedupe(ref for result in selected for ref in result.memory_feedback_refs)
        required = _dedupe(required_refs or [])
        all_refs = set([*evidence_refs, *receipt_refs, *finalgate_refs, *memory_refs])
        preserved = [ref for ref in required if ref in all_refs]
        pack = HarnessContextPack(
            mission_id=mission_id,
            session_id=session_id,
            safe_goal=safe_goal,
            safe_context_items=safe_context_items,
            evidence_refs=evidence_refs,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
            required_refs=required,
            required_refs_preserved=preserved,
            compressed=compressed,
            estimated_tokens_saved=tokens_saved,
        ).with_hash()
        self._write_json(
            self._entity_path(mission_id, "context_packs", session_id, pack.context_pack_id),
            pack.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_context_pack_created",
            safe_summary="Harness context pack created.",
            metadata={"session_id": session_id, "context_pack_id": pack.context_pack_id, "compressed": pack.compressed},
            receipt_refs=pack.receipt_refs,
            finalgate_certificate_refs=pack.finalgate_certificate_refs,
            memory_feedback_refs=pack.memory_feedback_refs,
        )
        self._record_metric(
            mission_id,
            metric_kind=TelemetryMetricKind.HARNESS_CONTEXT_TOKENS_SAVED,
            value=pack.estimated_tokens_saved,
            unit="tokens",
            safe_summary="Harness context tokens saved sample.",
            metadata={"session_id": session_id, "context_pack_id": pack.context_pack_id},
        )
        return pack

    def submit_worker_result(
        self,
        *,
        mission_id: str,
        session_id: str,
        request: HarnessWorkerRequest,
        safe_summary: str,
        output: dict[str, Any],
        evidence_refs: list[str],
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> HarnessWorkerResult:
        self._load_session(mission_id, session_id)
        self._write_json(
            self._entity_path(mission_id, "worker_requests", session_id, request.request_id),
            request.model_dump(mode="json"),
        )
        self._append_event(
            mission_id,
            event_type="harness_worker_requested",
            safe_summary="Harness worker-safe analysis requested.",
            metadata={"session_id": session_id, "request_id": request.request_id},
        )
        required_evidence_refs = int(request.result_contract.get("required_evidence_refs", 0) or 0)
        if len(evidence_refs) < required_evidence_refs:
            self._append_event(
                mission_id,
                event_type="harness_worker_rejected",
                safe_summary="Harness worker result rejected for missing evidence refs.",
                metadata={"session_id": session_id, "request_id": request.request_id},
            )
            raise HarnessRuntimeError("harness_worker_result_missing_required_evidence")
        result = HarnessWorkerResult(
            request_id=request.request_id,
            mission_id=mission_id,
            safe_summary=safe_summary,
            output=output,
            evidence_refs=evidence_refs,
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
            memory_feedback_refs=memory_feedback_refs or [],
            conflict_key=request.result_contract.get("conflict_key"),
        ).with_hash()
        self._write_json(
            self._entity_path(mission_id, "worker_results", session_id, result.worker_result_ref),
            result.safe_model_dump(),
        )
        self._append_event(
            mission_id,
            event_type="harness_worker_completed",
            safe_summary="Harness worker-safe result completed.",
            metadata={"session_id": session_id, "worker_result_ref": result.worker_result_ref},
            receipt_refs=result.receipt_refs,
            finalgate_certificate_refs=result.finalgate_certificate_refs,
            memory_feedback_refs=result.memory_feedback_refs,
        )
        return result

    def merge_worker_results(
        self,
        *,
        mission_id: str,
        session_id: str,
        results: list[HarnessWorkerResult],
    ) -> HarnessMergeDecision:
        self._load_session(mission_id, session_id)
        conflicts: list[HarnessConflictRecord] = []
        by_key: dict[str, list[HarnessWorkerResult]] = {}
        for result in results:
            if result.conflict_key:
                by_key.setdefault(result.conflict_key, []).append(result)
        for key, keyed_results in by_key.items():
            output_hashes = {stable_hash(result.output) for result in keyed_results}
            if len(keyed_results) > 1 and len(output_hashes) > 1:
                conflicts.append(
                    HarnessConflictRecord(
                        conflict_key=key,
                        result_refs=[result.worker_result_ref for result in keyed_results],
                        result_hashes=[result.result_hash for result in keyed_results],
                        safe_summary=f"Harness detected conflicting worker outputs for {key}.",
                    )
                )
        if conflicts:
            decision = HarnessMergeDecision(
                mission_id=mission_id,
                session_id=session_id,
                outcome="conflict",
                reasons=["harness_worker_conflict_detected"],
                result_refs=[result.worker_result_ref for result in results],
                conflict_records=conflicts,
                merge_success=False,
            )
            self._append_event(
                mission_id,
                event_type="harness_conflict_detected",
                safe_summary="Harness detected conflicting worker outputs.",
                metadata={"session_id": session_id, "conflict_count": len(conflicts)},
            )
            self._append_event(
                mission_id,
                event_type="harness_merge_rejected",
                safe_summary="Harness merge rejected conflicting worker outputs.",
                metadata={"session_id": session_id, "result_count": len(results)},
            )
            self._record_metric(
                mission_id,
                metric_kind=TelemetryMetricKind.HARNESS_CONFLICT_COUNT,
                value=len(conflicts),
                unit="count",
                safe_summary="Harness conflict count sample.",
                metadata={"session_id": session_id},
            )
            self._record_metric(
                mission_id,
                metric_kind=TelemetryMetricKind.HARNESS_MERGE_SUCCESS_RATE,
                value=0.0,
                safe_summary="Harness merge success rate sample.",
                metadata={"session_id": session_id},
            )
        else:
            decision = HarnessMergeDecision(
                mission_id=mission_id,
                session_id=session_id,
                outcome="merged",
                result_refs=[result.worker_result_ref for result in results],
                merge_success=True,
            )
            self._append_event(
                mission_id,
                event_type="harness_merge_completed",
                safe_summary="Harness merge completed.",
                metadata={"session_id": session_id, "result_count": len(results)},
            )
            self._record_metric(
                mission_id,
                metric_kind=TelemetryMetricKind.HARNESS_MERGE_SUCCESS_RATE,
                value=1.0,
                safe_summary="Harness merge success rate sample.",
                metadata={"session_id": session_id},
            )
        self._write_json(
            self._entity_path(mission_id, "merges", session_id, decision.merge_decision_id),
            decision.model_dump(mode="json"),
        )
        return decision

    def _assert_supported_mission(self, mission_id: str) -> None:
        try:
            self.kernel.store.load_record(mission_id)
        except Exception as exc:  # noqa: BLE001
            raise HarnessRuntimeError("harness_mission_not_found") from exc
        if self.config.require_certified_telemetry:
            telemetry = getattr(self.kernel, "telemetry_sink", None)
            if telemetry is None or not hasattr(telemetry, "certified_mode_status"):
                raise HarnessRuntimeError("harness_certified_telemetry_required")
            snapshot = telemetry.certified_mode_status()
            if not snapshot.certified_mode:
                raise HarnessRuntimeError("harness_certified_telemetry_required")

    def _assert_envelope_matches(self, mission_id: str, envelope: MissionAuthorityEnvelope) -> None:
        if envelope.id != mission_id:
            raise HarnessRuntimeError("harness_parent_envelope_mission_mismatch")
        if envelope.revoked_at is not None:
            raise HarnessRuntimeError("harness_parent_envelope_revoked")

    def _assert_model_contract_unchanged(
        self,
        *,
        provider_id: str | None,
        backend_id: str | None,
        model_id: str | None,
        requested_provider_id: str | None,
        requested_backend_id: str | None,
        requested_model_id: str | None,
    ) -> None:
        selected = {
            "provider": provider_id,
            "backend": backend_id,
            "model": model_id,
        }
        requested = {
            "provider": requested_provider_id,
            "backend": requested_backend_id,
            "model": requested_model_id,
        }
        if any(str(value).strip().lower() == "auto" for value in [*selected.values(), *requested.values()] if value is not None):
            raise HarnessRuntimeError("provider_backend_model_override_rejected")
        for key, requested_value in requested.items():
            if requested_value is None:
                continue
            if selected[key] != requested_value:
                raise HarnessRuntimeError("provider_backend_model_override_rejected")

    def _append_event(
        self,
        mission_id: str,
        *,
        event_type: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> None:
        self.kernel.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=redact_operator_value(metadata or {}),
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
            memory_feedback_refs=memory_feedback_refs or [],
        )

    def _record_metric(
        self,
        mission_id: str,
        *,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        telemetry = getattr(self.kernel, "telemetry_sink", None)
        store = getattr(telemetry, "store", None)
        if store is None:
            return
        try:
            store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.MODEL_AMPLIFICATION_HARNESS,
                    domain=TelemetryDomain.PRODUCT_POWER,
                    metric_kind=metric_kind,
                    value=value,
                    unit=unit,
                    safe_summary=safe_summary,
                    metadata=metadata or {},
                )
            )
        except Exception:
            return

    def _persist_session(self, session: AmplificationSession) -> None:
        self._write_json(
            self._entity_path(session.mission_id, "sessions", None, session.session_id),
            session.safe_model_dump(),
        )

    def _load_session(self, mission_id: str, session_id: str) -> AmplificationSession:
        path = self._entity_path(mission_id, "sessions", None, session_id)
        return AmplificationSession.model_validate_json(path.read_text(encoding="utf-8"))

    def _load_artifact(self, mission_id: str, artifact_ref: str) -> ContentAddressedArtifact:
        root = self._harness_root(mission_id) / _HARNESS_DIR_ALIASES["artifacts"]
        matches = list(root.glob(f"*/{_short_component(artifact_ref)}.json"))
        if not matches:
            raise HarnessRuntimeError("harness_artifact_not_found")
        return ContentAddressedArtifact.model_validate_json(matches[0].read_text(encoding="utf-8"))

    def _persist_edit_verification(self, verification: HashAnchoredEditVerification) -> None:
        self._write_json(
            self._entity_path(
                verification.mission_id,
                "edit_verifications",
                verification.session_id,
                verification.verification_id,
            ),
            verification.safe_model_dump(),
        )

    def _harness_root(self, mission_id: str) -> Path:
        return self.kernel.store.mission_dir(mission_id, create=True) / "harness"

    def _session_dir(self, mission_id: str, subdir: str, session_id: str | None) -> Path:
        alias = _HARNESS_DIR_ALIASES.get(subdir, subdir)
        if session_id is None:
            return self._harness_root(mission_id) / alias
        return self._harness_root(mission_id) / alias / _short_component(session_id)

    def _entity_path(self, mission_id: str, subdir: str, session_id: str | None, identifier: str) -> Path:
        return self._session_dir(mission_id, subdir, session_id) / f"{_short_component(identifier)}.json"

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.kernel.store.atomic_write_json(path, payload)


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


_HARNESS_DIR_ALIASES = {
    "sessions": "s",
    "artifacts": "a",
    "edit_proposals": "ep",
    "edit_verifications": "ev",
    "kernels": "k",
    "kernel_results": "kr",
    "tool_results": "t",
    "context_packs": "c",
    "worker_requests": "wrq",
    "worker_results": "wrs",
    "merges": "m",
}


def _short_component(value: str) -> str:
    return stable_hash(value)[:20]
