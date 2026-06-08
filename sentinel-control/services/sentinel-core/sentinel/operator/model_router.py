from __future__ import annotations

import os
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.catalog import (
    ProviderBackendProfile,
    ProviderCatalog,
    ProviderCatalogEntry,
    ProviderCatalogStatus,
    ProviderFamily,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.model_router_models import (
    HardwareInventorySnapshot,
    HardwareProbeResult,
    ModelBackendKind,
    ModelCandidate,
    ModelCandidateSource,
    ModelContextWindowProfile,
    ModelEnergyProfile,
    ModelHardwareProfile,
    ModelLatencyProfile,
    ModelPrivacyProfile,
    ModelQualityProfile,
    ModelRouterConfig,
    ModelRuntimeKind,
    RouteApprovalRecord,
    RouteCandidateScore,
    RouteDecision,
    RouteDecisionReceipt,
    RouteExecutionBinding,
    RouteObjective,
    RoutePolicy,
    RouteRejectionReason,
    RouteSimulationRequest,
    RouteSimulationResult,
    RuntimeAvailabilityProbe,
    RuntimeProbeStatus,
)
from sentinel.operator.store import MissionRunStore
from sentinel.shared.models import new_id
from sentinel.telemetry.models import (
    TelemetryDomain,
    TelemetryEventKind,
    TelemetryMetricKind,
    TelemetryMetricSample,
    TelemetrySourceSurface,
)


class ModelRouterRuntimeError(ValueError):
    """Raised when model routing would violate explicit route policy."""


class ModelRouterRuntime:
    """Sentinel-native model route proposal runtime.

    The router compares explicit model candidates and records route receipts.
    It never executes a model call, probes provider credentials, downloads
    models, starts local servers, or silently falls back to another model.
    """

    def __init__(
        self,
        *,
        store: MissionRunStore | None = None,
        run_root: Path | str | None = None,
        config: ModelRouterConfig | None = None,
        provider_catalog: ProviderCatalog | None = None,
    ) -> None:
        if store is None and run_root is None:
            raise ValueError("ModelRouterRuntime requires MissionRunStore or run_root")
        self.store = store or MissionRunStore(run_root)  # type: ignore[arg-type]
        self.config = config or ModelRouterConfig()
        self.provider_catalog = provider_catalog or build_default_provider_catalog()

    def create_route_request(
        self,
        *,
        mission_id: str,
        objective: RouteObjective,
        policy: RoutePolicy,
        user_model_contract: UserModelContract | None = None,
        explicit_contract_candidates: list[UserModelContract] | None = None,
        provider_catalog: ProviderCatalog | None = None,
        provider_ids: list[str] | None = None,
        local_runtime_descriptors: list[ModelCandidate] | None = None,
    ) -> RouteSimulationRequest:
        self.store.load_record(mission_id)
        route_id = new_id("model_route")
        policy = policy.with_hash()
        objective = objective.model_copy(update={"mission_id": mission_id}).with_hash()
        hardware_snapshot = self.capture_hardware_snapshot(mission_id=mission_id, route_id=route_id)
        candidates = self._discover_candidates(
            route_id=route_id,
            user_model_contract=user_model_contract,
            explicit_contract_candidates=explicit_contract_candidates or [],
            provider_catalog=provider_catalog or self.provider_catalog,
            provider_ids=provider_ids,
            local_runtime_descriptors=local_runtime_descriptors or [],
        )
        persisted_candidates = [self._register_candidate(mission_id, route_id, candidate) for candidate in candidates]
        runtime_probes = [
            self.probe_runtime_availability(mission_id=mission_id, route_id=route_id, candidate=candidate)
            for candidate in persisted_candidates
        ]
        request = RouteSimulationRequest(
            route_id=route_id,
            mission_id=mission_id,
            objective=objective,
            policy=policy,
            candidates=persisted_candidates,
            hardware_snapshot=hardware_snapshot,
            runtime_probes=runtime_probes,
        ).with_hash()
        self._write_route_artifact(mission_id, route_id, "request.json", request.safe_model_dump())
        self._append_route_event(
            mission_id,
            route_id,
            "model_router_simulation_started",
            "Model router route simulation request created.",
            metadata={
                "request_id": request.request_id,
                "policy_hash": policy.policy_hash,
                "candidate_count": len(persisted_candidates),
            },
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.MODEL_ROUTER_CANDIDATE_COUNT,
            len(persisted_candidates),
            "Model router candidate count recorded.",
            metadata={"route_id": route_id},
        )
        return request

    def capture_hardware_snapshot(self, *, mission_id: str, route_id: str) -> HardwareInventorySnapshot:
        snapshot = HardwareInventorySnapshot(
            mission_id=mission_id,
            route_id=route_id,
            platform_system=platform.system() or "unknown",
            platform_release=platform.release() or "unknown",
            machine=platform.machine() or "unknown",
            processor_hash=stable_hash(platform.processor() or "unknown"),
            python_runtime=f"{platform.python_implementation()} {platform.python_version()}",
            cpu_count=max(1, os.cpu_count() or 1),
            memory_total_mb=_safe_total_memory_mb(),
            gpu_available=None,
            gpu_probe_status="unknown",
            hardware_probe_result=HardwareProbeResult(),
        ).with_hash()
        self._write_route_artifact(mission_id, route_id, "hardware_snapshot.json", snapshot.safe_model_dump())
        self._append_route_event(
            mission_id,
            route_id,
            "model_router_hardware_snapshot_created",
            "Safe local hardware inventory snapshot created.",
            metadata={
                "snapshot_id": snapshot.snapshot_id,
                "cpu_count": snapshot.cpu_count,
                "memory_total_mb": snapshot.memory_total_mb,
                "gpu_probe_status": snapshot.gpu_probe_status,
            },
        )
        return snapshot

    def probe_runtime_availability(
        self,
        *,
        mission_id: str,
        route_id: str,
        candidate: ModelCandidate,
    ) -> RuntimeAvailabilityProbe:
        self._append_route_event(
            mission_id,
            route_id,
            "model_router_runtime_probe_started",
            "Model router runtime availability probe started.",
            metadata={"candidate_id": candidate.candidate_id},
        )
        start = time.perf_counter()
        endpoint = candidate.runtime_endpoint
        endpoint_is_loopback = bool(endpoint and _is_loopback_endpoint(endpoint))
        status = RuntimeProbeStatus.UNKNOWN
        safe_summary = "Runtime availability unknown; no provider call performed."
        latency_ms: float | None = None

        if candidate.is_local_runtime and endpoint and endpoint_is_loopback:
            available = _probe_loopback_socket(endpoint, timeout_seconds=self.config.safe_local_probe_timeout_seconds)
            latency_ms = round((time.perf_counter() - start) * 1000, 3)
            status = RuntimeProbeStatus.AVAILABLE if available else RuntimeProbeStatus.UNAVAILABLE
            safe_summary = "Local loopback runtime endpoint is reachable." if available else "Local loopback runtime endpoint is unavailable."
        elif endpoint and not endpoint_is_loopback:
            status = RuntimeProbeStatus.UNKNOWN
            safe_summary = "Remote provider availability not probed; no network scan or credential probe performed."
        elif candidate.is_local_runtime:
            status = RuntimeProbeStatus.UNKNOWN
            safe_summary = "Local runtime descriptor has no explicit loopback endpoint to probe."

        probe = RuntimeAvailabilityProbe(
            mission_id=mission_id,
            route_id=route_id,
            candidate_id=candidate.candidate_id,
            provider_id=candidate.provider_id,
            backend_id=candidate.backend_id,
            model_id=candidate.model_id,
            runtime_kind=candidate.runtime_kind,
            status=status,
            endpoint_ref_hash=stable_hash(endpoint) if endpoint else None,
            endpoint_is_loopback=endpoint_is_loopback,
            latency_ms=latency_ms,
            safe_summary=safe_summary,
        ).with_hash()
        self._write_route_artifact(
            mission_id,
            route_id,
            f"runtime_probes/{_safe_component(probe.probe_id)}.json",
            probe.safe_model_dump(),
        )
        self._append_route_event(
            mission_id,
            route_id,
            "model_router_runtime_probe_completed",
            "Model router runtime availability probe completed without provider execution.",
            metadata={
                "candidate_id": candidate.candidate_id,
                "probe_id": probe.probe_id,
                "status": probe.status.value,
                "endpoint_is_loopback": probe.endpoint_is_loopback,
            },
        )
        return probe

    def simulate_route(self, request: RouteSimulationRequest) -> RouteSimulationResult:
        if not request.verify_hash():
            raise ModelRouterRuntimeError("route request hash mismatch")
        scores = [
            _score_candidate(
                candidate,
                policy=request.policy,
                objective=request.objective,
                hardware_snapshot=request.hardware_snapshot,
                probe=_probe_for_candidate(request.runtime_probes, candidate.candidate_id),
            )
            for candidate in request.candidates
        ]
        viable = [score for score in scores if not score.rejection_reasons]
        selected = max(viable, key=lambda score: (score.overall_score, score.privacy_score, score.cost_score), default=None)
        rejected_candidate_ids = [score.candidate_id for score in scores if score.rejection_reasons]
        simulation = RouteSimulationResult(
            route_id=request.route_id,
            mission_id=request.mission_id,
            request_hash=request.request_hash,
            policy_hash=request.policy.policy_hash,
            objective_hash=request.objective.objective_hash,
            candidate_scores=scores,
            selected_candidate_id=selected.candidate_id if selected else None,
            rejected_candidate_ids=rejected_candidate_ids,
            estimated_cost_usd=selected.estimated_cost_usd if selected else None,
            estimated_latency_seconds=selected.estimated_latency_seconds if selected else None,
            privacy_posture=selected.privacy_posture if selected else "no route accepted",
            hardware_fit=selected.hardware_fit if selected else "no route accepted",
            context_fit=selected.context_fit if selected else "no route accepted",
            requires_operator_approval=bool(selected and _requires_operator_approval(selected, request.policy)),
        ).with_hash()
        self._write_route_artifact(request.mission_id, request.route_id, "simulation.json", simulation.safe_model_dump())
        self._append_route_event(
            request.mission_id,
            request.route_id,
            "model_router_simulation_completed",
            "Model router simulation completed.",
            metadata={
                "simulation_id": simulation.simulation_id,
                "selected_candidate_id": simulation.selected_candidate_id,
                "rejected_candidate_count": len(rejected_candidate_ids),
            },
        )
        self._record_metric(
            request.mission_id,
            TelemetryMetricKind.MODEL_ROUTER_CANDIDATE_REJECTION_COUNT,
            len(rejected_candidate_ids),
            "Model router rejected candidate count recorded.",
            metadata={"route_id": request.route_id},
        )
        self._record_metric(
            request.mission_id,
            TelemetryMetricKind.MODEL_ROUTER_POLICY_REJECT_COUNT,
            sum(1 for score in scores for reason in score.rejection_reasons if reason.policy_field),
            "Model router policy rejection count recorded.",
            metadata={"route_id": request.route_id},
        )
        if selected is not None:
            self._record_selected_score_metrics(request.mission_id, request.route_id, selected)
        else:
            self._append_route_event(
                request.mission_id,
                request.route_id,
                "model_router_policy_rejected",
                "Model router policy rejected all candidates.",
                metadata={"rejected_candidate_count": len(rejected_candidate_ids)},
            )
        return simulation

    def decide_route(self, simulation: RouteSimulationResult) -> RouteDecision:
        if not simulation.verify_hash():
            raise ModelRouterRuntimeError("route simulation hash mismatch")
        rejected_reasons = {
            score.candidate_id: score.rejection_reasons for score in simulation.candidate_scores if score.rejection_reasons
        }
        decision = RouteDecision(
            route_id=simulation.route_id,
            mission_id=simulation.mission_id,
            route_policy_ref=simulation.policy_hash,
            route_policy_hash=simulation.policy_hash,
            simulation_id=simulation.simulation_id,
            simulation_hash=simulation.simulation_hash,
            candidate_scores=simulation.candidate_scores,
            selected_candidate_id=simulation.selected_candidate_id,
            rejected_candidate_ids=simulation.rejected_candidate_ids,
            rejected_candidate_reasons=rejected_reasons,
            estimated_cost_usd=simulation.estimated_cost_usd,
            estimated_latency_seconds=simulation.estimated_latency_seconds,
            privacy_posture=simulation.privacy_posture,
            hardware_fit=simulation.hardware_fit,
            context_fit=simulation.context_fit,
            requires_operator_approval=simulation.requires_operator_approval,
            accepted=simulation.selected_candidate_id is not None,
            safe_summary="Model route accepted as advisory data only." if simulation.selected_candidate_id else "Model route rejected; no candidate satisfied policy.",
        ).with_hash()
        self._write_decision(decision)
        event_type = "model_router_decision_created" if decision.accepted else "model_router_decision_rejected"
        self._append_route_event(
            decision.mission_id,
            decision.route_id,
            event_type,
            decision.safe_summary,
            metadata={
                "decision_id": decision.decision_id,
                "selected_candidate_id": decision.selected_candidate_id,
                "requires_operator_approval": decision.requires_operator_approval,
            },
        )
        receipt = self.create_route_receipt(decision)
        decision = decision.model_copy(
            update={"route_receipt_ref": receipt.receipt_id, "route_receipt_hash": receipt.receipt_hash}
        ).with_hash()
        self._write_decision(decision)
        return decision

    def record_route_approval(
        self,
        decision: RouteDecision,
        *,
        approved_by: str,
        approval_source: str,
        safe_summary: str,
    ) -> RouteApprovalRecord:
        try:
            approval = RouteApprovalRecord(
                route_id=decision.route_id,
                decision_id=decision.decision_id,
                mission_id=decision.mission_id,
                approved_by=approved_by,
                approval_source=approval_source,
                safe_summary=safe_summary,
            ).with_hash()
        except ValueError as exc:
            raise ModelRouterRuntimeError(str(exc)) from exc
        self._write_route_artifact(
            decision.mission_id,
            decision.route_id,
            "approval.json",
            approval.safe_model_dump(),
        )
        self._append_route_event(
            decision.mission_id,
            decision.route_id,
            "model_router_approval_recorded",
            "Operator model route approval recorded.",
            metadata={"approval_id": approval.approval_id, "decision_id": decision.decision_id},
        )
        self._record_metric(
            decision.mission_id,
            TelemetryMetricKind.MODEL_ROUTER_ROUTE_APPROVAL_RATE,
            1.0,
            "Model router approval recorded.",
            metadata={"route_id": decision.route_id},
        )
        return approval

    def bind_user_model_contract(
        self,
        decision: RouteDecision,
        *,
        user_model_contract: UserModelContract,
        approval_record: RouteApprovalRecord | None = None,
    ) -> RouteExecutionBinding:
        if not decision.accepted or decision.selected_candidate_id is None:
            raise ModelRouterRuntimeError("cannot bind a rejected route")
        if decision.requires_operator_approval and approval_record is None:
            raise ModelRouterRuntimeError("operator approval required before model route binding")
        if approval_record is not None and not approval_record.verify_hash():
            raise ModelRouterRuntimeError("route approval hash mismatch")
        score = self._selected_score(decision)
        if (
            user_model_contract.selected_provider_id != score.provider_id
            or user_model_contract.selected_backend_id != score.backend_id
            or user_model_contract.selected_model != score.model_id
        ):
            raise ModelRouterRuntimeError("selected UserModelContract identity mismatch")
        if user_model_contract.model_override_attempted:
            raise ModelRouterRuntimeError("UserModelContract override attempt rejected")
        binding = RouteExecutionBinding(
            route_id=decision.route_id,
            decision_id=decision.decision_id,
            candidate_id=decision.selected_candidate_id,
            mission_id=decision.mission_id,
            selected_provider_id=user_model_contract.selected_provider_id,
            selected_backend_id=user_model_contract.selected_backend_id,
            selected_model_id=user_model_contract.selected_model,
            user_model_contract=user_model_contract,
            operator_approval_ref=approval_record.approval_id if approval_record else None,
        ).with_hash()
        self._write_route_artifact(
            decision.mission_id,
            decision.route_id,
            "binding.json",
            binding.safe_model_dump(),
        )
        self._append_route_event(
            decision.mission_id,
            decision.route_id,
            "model_router_binding_created",
            "Explicit UserModelContract binding created from approved route.",
            metadata={
                "binding_id": binding.binding_id,
                "provider_id": binding.selected_provider_id,
                "backend_id": binding.selected_backend_id,
                "model_id": binding.selected_model_id,
            },
        )
        self.create_route_receipt(decision, approval_record=approval_record, binding=binding)
        return binding

    def create_route_receipt(
        self,
        decision: RouteDecision,
        *,
        approval_record: RouteApprovalRecord | None = None,
        binding: RouteExecutionBinding | None = None,
    ) -> RouteDecisionReceipt:
        scores = decision.candidate_scores
        selected = self._selected_score(decision) if decision.selected_candidate_id else None
        telemetry_refs = [
            event.event_hash
            for event in self.store.load_events(decision.mission_id)
            if event.event_type.startswith("model_router_") and event.metadata.get("route_id") == decision.route_id
        ]
        receipt = RouteDecisionReceipt(
            route_id=decision.route_id,
            decision_id=decision.decision_id,
            mission_id=decision.mission_id,
            candidate_ids=[score.candidate_id for score in scores],
            policy_hash=decision.route_policy_hash,
            simulation_hash=decision.simulation_hash,
            selected_candidate_id=decision.selected_candidate_id,
            rejection_reasons=decision.rejected_candidate_reasons,
            estimated_cost_usd=decision.estimated_cost_usd,
            estimated_latency_seconds=decision.estimated_latency_seconds,
            privacy_summary=decision.privacy_posture,
            hardware_summary=decision.hardware_fit,
            context_summary=decision.context_fit,
            operator_approval_ref=approval_record.approval_id if approval_record else None,
            user_model_contract_binding_hash=binding.binding_hash if binding else None,
            telemetry_refs=telemetry_refs,
            selected_provider_id=selected.provider_id if selected else None,
            selected_backend_id=selected.backend_id if selected else None,
            selected_model_id=selected.model_id if selected else None,
        ).with_hash()
        self._write_route_artifact(
            decision.mission_id,
            decision.route_id,
            "receipt.json",
            receipt.safe_model_dump(),
        )
        updated_decision = decision.model_copy(
            update={"route_receipt_ref": receipt.receipt_id, "route_receipt_hash": receipt.receipt_hash}
        ).with_hash()
        self._write_decision(updated_decision)
        return receipt

    def load_route_receipt(self, mission_id: str, route_id: str) -> RouteDecisionReceipt:
        path = self.route_root(mission_id, route_id) / "receipt.json"
        return RouteDecisionReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_route_decision(self, mission_id: str, route_id: str) -> RouteDecision:
        path = self.route_root(mission_id, route_id) / "decision.json"
        return RouteDecision.model_validate_json(path.read_text(encoding="utf-8"))

    def block_fallback_attempt(
        self,
        *,
        mission_id: str,
        route_id: str,
        attempted_provider_id: str,
        attempted_backend_id: str,
        attempted_model_id: str,
        safe_reason: str,
    ):
        event = self._append_route_event(
            mission_id,
            route_id,
            "model_router_fallback_blocked",
            safe_reason,
            metadata={
                "attempted_provider_id": attempted_provider_id,
                "attempted_backend_id": attempted_backend_id,
                "attempted_model_id": attempted_model_id,
            },
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.MODEL_ROUTER_FALLBACK_BLOCK_COUNT,
            1,
            "Model router fallback attempt blocked.",
            metadata={"route_id": route_id},
        )
        return event

    def route_root(self, mission_id: str, route_id: str, *, create: bool = True) -> Path:
        root = self.store.mission_dir(mission_id, create=create) / "model_router" / _safe_component(route_id)
        if create:
            root.mkdir(parents=True, exist_ok=True)
        return root

    def _discover_candidates(
        self,
        *,
        route_id: str,
        user_model_contract: UserModelContract | None,
        explicit_contract_candidates: list[UserModelContract],
        provider_catalog: ProviderCatalog,
        provider_ids: list[str] | None,
        local_runtime_descriptors: list[ModelCandidate],
    ) -> list[ModelCandidate]:
        candidates: list[ModelCandidate] = []
        if user_model_contract is not None:
            candidates.append(self._candidate_from_contract(user_model_contract, route_id=route_id, provider_catalog=provider_catalog))
        for contract in explicit_contract_candidates:
            candidates.append(self._candidate_from_contract(contract, route_id=route_id, provider_catalog=provider_catalog))
        if provider_ids:
            for provider_id in provider_ids:
                entry = provider_catalog.get(provider_id)
                for backend in entry.backends:
                    for model_id in backend.supported_models:
                        candidates.append(self._candidate_from_catalog_entry(entry, backend, model_id=model_id, route_id=route_id))
        for descriptor in local_runtime_descriptors:
            candidates.append(descriptor.model_copy(update={"route_id": route_id}).with_hash())
        return candidates

    def _candidate_from_contract(
        self,
        contract: UserModelContract,
        *,
        route_id: str,
        provider_catalog: ProviderCatalog,
    ) -> ModelCandidate:
        entry: ProviderCatalogEntry | None = None
        backend: ProviderBackendProfile | None = None
        try:
            entry = provider_catalog.get(contract.selected_provider_id)
            backend = next((item for item in entry.backends if item.backend_id == contract.selected_backend_id), None)
        except LookupError:
            entry = None
        is_local = bool(entry and _is_local_catalog_entry(entry))
        runtime_kind = _runtime_kind_for_provider(contract.selected_provider_id, entry.family if entry else None)
        backend_kind = _backend_kind_for_backend(backend)
        candidate = ModelCandidate(
            route_id=route_id,
            source=ModelCandidateSource.EXPLICIT_USER_MODEL_CONTRACT,
            runtime_kind=runtime_kind,
            backend_kind=backend_kind,
            provider_id=contract.selected_provider_id,
            backend_id=contract.selected_backend_id,
            model_id=contract.selected_model,
            display_name=f"Explicit {contract.selected_provider_id}/{contract.selected_model}",
            runtime_endpoint=None,
            selected_user_model_contract_id=contract.id,
            user_model_contract_hash=stable_hash(contract.model_dump(mode="json")),
            cost_profile=contract.cost_profile,
            capability_profile=contract.capability_profile,
            latency_profile=_latency_profile_from_catalog(entry),
            quality_profile=_quality_profile_from_catalog(entry, contract.quality_expectation.expected_quality),
            privacy_profile=ModelPrivacyProfile(
                local_only=is_local,
                cloud_provider=not is_local,
                privacy_score=1.0 if is_local else 0.55,
                prompt_retention="local_runtime" if is_local else "provider_policy_unknown",
                safe_summary="Explicit user-selected local model contract." if is_local else "Explicit user-selected cloud model contract.",
            ),
            context_window_profile=ModelContextWindowProfile(
                candidate_context_window_tokens=contract.cost_profile.context_window_tokens
            ),
            energy_profile=ModelEnergyProfile(energy_estimate_status="unknown"),
            metadata={
                "contract_id": contract.id,
                "routing_policy": "explicit_contract_candidate",
            },
        )
        return candidate.with_hash()

    def _candidate_from_catalog_entry(
        self,
        entry: ProviderCatalogEntry,
        backend: ProviderBackendProfile,
        *,
        model_id: str,
        route_id: str,
    ) -> ModelCandidate:
        is_local = _is_local_catalog_entry(entry)
        context_window = 16_000 if not is_local else 8_192
        cost_profile = (
            ModelCostProfile(
                model_name=model_id,
                input_usd_per_1m=0.0,
                output_usd_per_1m=0.0,
                context_window_tokens=context_window,
                notes=["local runtime descriptor cost is local-only/unknown billing"],
            )
            if is_local
            else None
        )
        candidate = ModelCandidate(
            route_id=route_id,
            source=ModelCandidateSource.PROVIDER_CATALOG,
            runtime_kind=_runtime_kind_for_provider(entry.provider_id, entry.family),
            backend_kind=_backend_kind_for_backend(backend),
            provider_id=entry.provider_id,
            backend_id=backend.backend_id,
            model_id=model_id,
            display_name=f"{entry.display_name} {model_id}",
            runtime_endpoint=None,
            provider_catalog_ref_hash=stable_hash(
                {
                    "provider_id": entry.provider_id,
                    "backend_id": backend.backend_id,
                    "model_id": model_id,
                    "status": entry.status.value,
                }
            ),
            cost_profile=cost_profile,
            capability_profile=ModelCapabilityProfile(
                model_name=model_id,
                context_window_tokens=context_window,
                supports_tool_calling=False,
                supports_vision=entry.capability_flags.vision,
                strengths=["catalog candidate"],
                limitations=["descriptor only; not execution binding"],
            ),
            latency_profile=_latency_profile_from_catalog(entry),
            quality_profile=_quality_profile_from_catalog(entry, entry.recommendation.reliability_class if entry.recommendation else entry.status.value),
            privacy_profile=ModelPrivacyProfile(
                local_only=is_local,
                cloud_provider=not is_local,
                privacy_score=1.0 if is_local else 0.45,
                prompt_retention="local_runtime" if is_local else "provider_policy_unknown",
                safe_summary="Catalog local runtime descriptor." if is_local else "Catalog cloud/API descriptor.",
            ),
            energy_profile=ModelEnergyProfile(energy_estimate_status="unknown"),
            context_window_profile=ModelContextWindowProfile(candidate_context_window_tokens=context_window),
            metadata={
                "catalog_status": entry.status.value,
                "credential_source_type": entry.credential_policy.credential_source_type,
                "required_for_real_call": entry.credential_policy.required_for_real_call,
            },
        )
        return candidate.with_hash()

    def _register_candidate(self, mission_id: str, route_id: str, candidate: ModelCandidate) -> ModelCandidate:
        candidate = candidate.model_copy(update={"route_id": route_id}).with_hash()
        self._write_route_artifact(
            mission_id,
            route_id,
            f"candidates/{_safe_component(candidate.candidate_id)}.json",
            candidate.safe_model_dump(),
        )
        self._append_route_event(
            mission_id,
            route_id,
            "model_router_candidate_registered",
            "Model router candidate registered as data-only route option.",
            metadata={
                "candidate_id": candidate.candidate_id,
                "provider_id": candidate.provider_id,
                "backend_id": candidate.backend_id,
                "model_id": candidate.model_id,
                "source": candidate.source.value,
            },
        )
        return candidate

    def _write_decision(self, decision: RouteDecision) -> None:
        self._write_route_artifact(
            decision.mission_id,
            decision.route_id,
            "decision.json",
            decision.safe_model_dump(),
        )

    def _write_route_artifact(self, mission_id: str | None, route_id: str, relative_path: str, payload: Any) -> None:
        if mission_id is None:
            raise ModelRouterRuntimeError("mission_id is required for route persistence")
        path = self.route_root(mission_id, route_id) / relative_path
        self.store.atomic_write_json(path, payload)

    def _append_route_event(
        self,
        mission_id: str | None,
        route_id: str,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ):
        if mission_id is None:
            raise ModelRouterRuntimeError("mission_id is required for route events")
        metadata = {**(metadata or {}), "route_id": route_id}
        return self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata,
        )

    def _record_metric(
        self,
        mission_id: str | None,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ):
        if mission_id is None:
            return None
        sink = getattr(self.store, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "record_metric"):
            return None
        domain = TelemetryDomain.COST if "cost" in metric_kind.value else TelemetryDomain.PRODUCT_POWER
        return sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MODEL_ROUTER,
                domain=domain,
                metric_kind=metric_kind,
                value=value,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )

    def _record_selected_score_metrics(self, mission_id: str | None, route_id: str, selected: RouteCandidateScore) -> None:
        metrics = [
            (TelemetryMetricKind.MODEL_ROUTER_ESTIMATED_COST_DELTA, selected.estimated_cost_usd or 0.0),
            (TelemetryMetricKind.MODEL_ROUTER_ESTIMATED_LATENCY_DELTA, selected.estimated_latency_seconds or 0.0),
            (TelemetryMetricKind.MODEL_ROUTER_CONTEXT_FIT_SCORE, selected.context_fit_score),
            (TelemetryMetricKind.MODEL_ROUTER_HARDWARE_FIT_SCORE, selected.hardware_fit_score),
            (TelemetryMetricKind.MODEL_ROUTER_PRIVACY_SCORE, selected.privacy_score),
            (TelemetryMetricKind.MODEL_ROUTER_QUALITY_SCORE, selected.quality_score),
        ]
        for kind, value in metrics:
            self._record_metric(
                mission_id,
                kind,
                value,
                f"Model router {kind.value} recorded.",
                metadata={"route_id": route_id, "candidate_id": selected.candidate_id},
            )

    def _selected_score(self, decision: RouteDecision) -> RouteCandidateScore:
        score = next((item for item in decision.candidate_scores if item.candidate_id == decision.selected_candidate_id), None)
        if score is None:
            raise ModelRouterRuntimeError("selected route candidate score missing")
        return score


def _score_candidate(
    candidate: ModelCandidate,
    *,
    policy: RoutePolicy,
    objective: RouteObjective,
    hardware_snapshot: HardwareInventorySnapshot,
    probe: RuntimeAvailabilityProbe | None,
) -> RouteCandidateScore:
    rejection_reasons: list[RouteRejectionReason] = []
    required_context = policy.context_window_requirement or objective.required_context_tokens or 1_000
    context_profile = (
        candidate.context_window_profile or ModelContextWindowProfile(candidate_context_window_tokens=8_000)
    ).for_requirement(required_context)
    estimated_cost = _estimated_cost(candidate, required_context)
    estimated_latency = _estimated_latency(candidate, probe)
    quality_score = candidate.quality_profile.quality_score
    privacy_score = candidate.privacy_profile.privacy_score
    context_fit_score = context_profile.context_fit_score
    hardware_fit_score = _hardware_fit_score(candidate, hardware_snapshot)
    reliability_score = _reliability_score(candidate)

    _policy_rejections(
        candidate=candidate,
        policy=policy,
        quality_score=quality_score,
        estimated_cost=estimated_cost,
        estimated_latency=estimated_latency,
        context_profile=context_profile,
        rejection_reasons=rejection_reasons,
    )

    if probe and probe.status is RuntimeProbeStatus.UNAVAILABLE and candidate.is_local_runtime:
        rejection_reasons.append(
            RouteRejectionReason(
                code="runtime_unavailable",
                detail="local runtime endpoint was explicitly probed and unavailable",
                policy_field="runtime_availability",
            )
        )

    cost_score = _cost_score(estimated_cost, policy.max_estimated_cost_usd)
    latency_score = _latency_score(estimated_latency, policy.max_estimated_latency_seconds)
    overall = (
        (0.24 * quality_score)
        + (0.18 * cost_score)
        + (0.14 * latency_score)
        + (0.18 * privacy_score)
        + (0.12 * hardware_fit_score)
        + (0.10 * context_fit_score)
        + (0.04 * (reliability_score if reliability_score is not None else 0.5))
    )
    if rejection_reasons:
        overall = 0.0
    return RouteCandidateScore(
        candidate_id=candidate.candidate_id,
        provider_id=candidate.provider_id,
        backend_id=candidate.backend_id,
        model_id=candidate.model_id,
        quality_score=round(quality_score, 6),
        cost_score=round(cost_score, 6),
        latency_score=round(latency_score, 6),
        privacy_score=round(privacy_score, 6),
        hardware_fit_score=round(hardware_fit_score, 6),
        context_fit_score=round(context_fit_score, 6),
        energy_score=candidate.energy_profile.energy_score,
        reliability_score=reliability_score,
        policy_fit=not rejection_reasons,
        overall_score=round(max(0.0, min(1.0, overall)), 6),
        estimated_cost_usd=estimated_cost,
        estimated_latency_seconds=estimated_latency,
        privacy_posture="local" if candidate.is_local_runtime else "cloud_or_remote_descriptor",
        hardware_fit="local_fit" if hardware_fit_score >= 0.75 else "hardware_fit_unknown_or_low",
        context_fit="fits_required_context" if context_profile.fits_required_context else "context_window_too_small",
        rejection_reasons=rejection_reasons,
    )


def _policy_rejections(
    *,
    candidate: ModelCandidate,
    policy: RoutePolicy,
    quality_score: float,
    estimated_cost: float | None,
    estimated_latency: float | None,
    context_profile: ModelContextWindowProfile,
    rejection_reasons: list[RouteRejectionReason],
) -> None:
    if policy.local_only and not candidate.is_local_runtime:
        rejection_reasons.append(
            RouteRejectionReason(
                code="local_only",
                detail="route policy requires a local runtime candidate",
                policy_field="local_only",
            )
        )
    if not policy.cloud_allowed and not candidate.is_local_runtime:
        rejection_reasons.append(
            RouteRejectionReason(
                code="cloud_not_allowed",
                detail="route policy does not allow cloud/API descriptor candidates",
                policy_field="cloud_allowed",
            )
        )
    if policy.allowed_provider_ids and candidate.provider_id not in set(policy.allowed_provider_ids):
        rejection_reasons.append(
            RouteRejectionReason(code="provider_not_allowed", detail="provider is not in allowed_provider_ids", policy_field="allowed_provider_ids")
        )
    if policy.allowed_backend_ids and candidate.backend_id not in set(policy.allowed_backend_ids):
        rejection_reasons.append(
            RouteRejectionReason(code="backend_not_allowed", detail="backend is not in allowed_backend_ids", policy_field="allowed_backend_ids")
        )
    if policy.allowed_model_ids and candidate.model_id not in set(policy.allowed_model_ids):
        rejection_reasons.append(
            RouteRejectionReason(code="model_not_allowed", detail="model is not in allowed_model_ids", policy_field="allowed_model_ids")
        )
    if candidate.provider_id in set(policy.blocked_provider_ids):
        rejection_reasons.append(RouteRejectionReason(code="blocked_provider", detail="provider is blocked by policy", policy_field="blocked_provider_ids"))
    if candidate.backend_id in set(policy.blocked_backend_ids):
        rejection_reasons.append(RouteRejectionReason(code="blocked_backend", detail="backend is blocked by policy", policy_field="blocked_backend_ids"))
    if candidate.model_id in set(policy.blocked_model_ids):
        rejection_reasons.append(RouteRejectionReason(code="blocked_model", detail="model is blocked by policy", policy_field="blocked_model_ids"))
    if quality_score < policy.quality_floor:
        rejection_reasons.append(RouteRejectionReason(code="quality_floor", detail="quality estimate is below route policy floor", policy_field="quality_floor"))
    if policy.max_estimated_cost_usd is not None and estimated_cost is not None and estimated_cost > policy.max_estimated_cost_usd:
        rejection_reasons.append(RouteRejectionReason(code="max_estimated_cost", detail="estimated route cost exceeds policy", policy_field="max_estimated_cost_usd"))
    if policy.max_estimated_latency_seconds is not None and estimated_latency is not None and estimated_latency > policy.max_estimated_latency_seconds:
        rejection_reasons.append(RouteRejectionReason(code="max_estimated_latency", detail="estimated route latency exceeds policy", policy_field="max_estimated_latency_seconds"))
    if policy.context_window_requirement and not context_profile.fits_required_context:
        rejection_reasons.append(RouteRejectionReason(code="context_window_requirement", detail="candidate context window does not fit policy", policy_field="context_window_requirement"))
    if policy.hardware_requirement and "gpu" in policy.hardware_requirement.lower() and not candidate.is_local_runtime:
        rejection_reasons.append(RouteRejectionReason(code="hardware_requirement", detail="hardware requirement cannot be satisfied by remote descriptor", policy_field="hardware_requirement"))


def _estimated_cost(candidate: ModelCandidate, required_context_tokens: int) -> float | None:
    if candidate.cost_profile is None:
        return None
    projection = candidate.cost_profile.project(
        input_tokens=max(1, required_context_tokens),
        output_tokens=min(1_000, max(100, required_context_tokens // 4)),
        retry_budget=0,
    )
    return projection.total_estimated_usd


def _estimated_latency(candidate: ModelCandidate, probe: RuntimeAvailabilityProbe | None) -> float | None:
    if probe and probe.latency_ms is not None:
        return round(probe.latency_ms / 1000, 6)
    if candidate.latency_profile.estimated_latency_seconds is not None:
        return candidate.latency_profile.estimated_latency_seconds
    latency_class = candidate.latency_profile.latency_class.lower()
    return {"low": 2.0, "medium": 8.0, "high": 20.0, "diagnostic": 25.0}.get(latency_class, 12.0)


def _cost_score(estimated_cost: float | None, max_cost: float | None) -> float:
    if estimated_cost is None:
        return 0.5
    if max_cost is None or max_cost == 0:
        return 1.0 if estimated_cost == 0 else 0.65
    return round(max(0.0, min(1.0, 1.0 - (estimated_cost / max_cost))), 6)


def _latency_score(estimated_latency: float | None, max_latency: float | None) -> float:
    if estimated_latency is None:
        return 0.5
    if max_latency is None or max_latency == 0:
        return 0.8 if estimated_latency <= 10 else 0.5
    return round(max(0.0, min(1.0, 1.0 - (estimated_latency / max_latency))), 6)


def _hardware_fit_score(candidate: ModelCandidate, snapshot: HardwareInventorySnapshot) -> float:
    if not candidate.is_local_runtime:
        return 0.7
    if snapshot.memory_total_mb is None:
        return 0.75 if snapshot.cpu_count >= 2 else 0.55
    min_memory = candidate.hardware_profile.min_memory_mb if candidate.hardware_profile else 0
    if min_memory and snapshot.memory_total_mb < min_memory:
        return 0.25
    return 1.0 if snapshot.cpu_count >= 2 else 0.75


def _reliability_score(candidate: ModelCandidate) -> float | None:
    summary = " ".join(
        [
            candidate.quality_profile.evidence_summary,
            str(candidate.metadata.get("catalog_status", "")),
        ]
    ).lower()
    if "success" in summary or "active" in summary:
        return 0.75
    if "diagnostic" in summary:
        return 0.45
    if candidate.is_local_runtime:
        return 0.55
    return None


def _requires_operator_approval(score: RouteCandidateScore, policy: RoutePolicy) -> bool:
    if policy.operator_confirmation_required:
        return True
    return score.privacy_posture != "local"


def _probe_for_candidate(probes: Iterable[RuntimeAvailabilityProbe], candidate_id: str) -> RuntimeAvailabilityProbe | None:
    return next((probe for probe in probes if probe.candidate_id == candidate_id), None)


def _is_loopback_endpoint(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if host is None:
        return False
    normalized = host.lower().strip("[]")
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return socket.gethostbyname(normalized).startswith("127.")
    except OSError:
        return False


def _probe_loopback_socket(endpoint: str, *, timeout_seconds: float) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if host is None:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _safe_total_memory_mb() -> int | None:
    if sys.platform.startswith("win"):
        return _windows_total_memory_mb()
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int((pages * page_size) / (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return None


def _windows_total_memory_mb() -> int | None:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys / (1024 * 1024))
    except Exception:
        return None
    return None


def _is_local_catalog_entry(entry: ProviderCatalogEntry) -> bool:
    return entry.credential_policy.credential_source_type == "local_none" or bool(entry.capability_flags.local_runtime)


def _runtime_kind_for_provider(provider_id: str, family: ProviderFamily | None) -> ModelRuntimeKind:
    if provider_id == "ollama":
        return ModelRuntimeKind.OLLAMA
    if provider_id == "lmstudio":
        return ModelRuntimeKind.OPENAI_COMPATIBLE
    if family is ProviderFamily.OPENAI_NATIVE:
        return ModelRuntimeKind.OPENAI_NATIVE
    if family is ProviderFamily.ANTHROPIC_MESSAGES_NATIVE:
        return ModelRuntimeKind.ANTHROPIC_MESSAGES
    if family is ProviderFamily.GEMINI_NATIVE:
        return ModelRuntimeKind.GEMINI_NATIVE
    if family is ProviderFamily.DEEPSEEK_COMPATIBLE:
        return ModelRuntimeKind.DEEPSEEK_COMPATIBLE
    if family is ProviderFamily.MISTRAL_NATIVE_OR_COMPATIBLE:
        return ModelRuntimeKind.MISTRAL_COMPATIBLE
    if family is ProviderFamily.XAI_COMPATIBLE_OR_NATIVE:
        return ModelRuntimeKind.XAI_COMPATIBLE
    if family is ProviderFamily.COHERE_NATIVE:
        return ModelRuntimeKind.COHERE_NATIVE
    return ModelRuntimeKind.OPENAI_COMPATIBLE if family else ModelRuntimeKind.UNKNOWN


def _backend_kind_for_backend(backend: ProviderBackendProfile | None) -> ModelBackendKind:
    if backend is None:
        return ModelBackendKind.UNKNOWN
    if backend.runtime == "responses":
        return ModelBackendKind.OPENAI_RESPONSES
    if backend.runtime == "messages":
        return ModelBackendKind.ANTHROPIC_MESSAGES
    if backend.runtime == "generate_content":
        return ModelBackendKind.GEMINI_GENERATE_CONTENT
    if backend.runtime == "chat_completions":
        return ModelBackendKind.OPENAI_COMPATIBLE_CHAT
    return ModelBackendKind.DESCRIPTOR_ONLY


def _latency_profile_from_catalog(entry: ProviderCatalogEntry | None) -> ModelLatencyProfile:
    if entry is not None and _is_local_catalog_entry(entry):
        return ModelLatencyProfile(latency_class="local_metadata_estimate", estimated_latency_seconds=4.0)
    if entry is None or entry.recommendation is None:
        return ModelLatencyProfile(latency_class="unknown", estimated_latency_seconds=12.0)
    latency_class = entry.recommendation.latency_class or "unknown"
    seconds = {"low": 2.0, "medium": 8.0, "high": 20.0, "diagnostic": 25.0}.get(latency_class, 12.0)
    return ModelLatencyProfile(latency_class=latency_class, estimated_latency_seconds=seconds)


def _quality_profile_from_catalog(entry: ProviderCatalogEntry | None, summary: str) -> ModelQualityProfile:
    if entry is None:
        return ModelQualityProfile(quality_score=0.6, evidence_summary=summary)
    if entry.status is ProviderCatalogStatus.ACTIVE:
        score = 0.72
    elif entry.status is ProviderCatalogStatus.LOCAL_ONLY:
        score = 0.62
    elif entry.status is ProviderCatalogStatus.DIAGNOSTIC:
        score = 0.45
    else:
        score = 0.4
    return ModelQualityProfile(quality_score=score, evidence_summary=f"catalog_status={entry.status.value}; {summary}")


def _safe_component(value: str) -> str:
    return stable_hash(value)[:24]
