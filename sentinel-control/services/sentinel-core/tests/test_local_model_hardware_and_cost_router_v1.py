from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.model_router import ModelRouterRuntime, ModelRouterRuntimeError
from sentinel.operator.model_router_models import (
    ModelBackendKind,
    ModelCandidate,
    ModelCandidateSource,
    ModelContextWindowProfile,
    ModelEnergyProfile,
    ModelPrivacyProfile,
    ModelRouterConfig,
    ModelRuntimeKind,
    RouteObjective,
    RoutePolicy,
    RuntimeProbeStatus,
)
from sentinel.operator.model_router_replay import ModelRouterReplayBuilder
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_candidate_discovery_normalizes_explicit_contract_and_provider_catalog(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")

    request = runtime.create_route_request(
        mission_id=mission_id,
        objective=_objective(mission_id),
        policy=RoutePolicy(allowed_provider_ids=["ollama", "groq"]),
        user_model_contract=contract,
        provider_catalog=build_default_provider_catalog(),
        provider_ids=["ollama", "groq"],
    )

    explicit = next(candidate for candidate in request.candidates if candidate.source is ModelCandidateSource.EXPLICIT_USER_MODEL_CONTRACT)
    catalog_groq = next(candidate for candidate in request.candidates if candidate.source is ModelCandidateSource.PROVIDER_CATALOG and candidate.provider_id == "groq")

    assert explicit.provider_id == "ollama"
    assert explicit.backend_id == "ollama_openai_compatible_chat"
    assert explicit.model_id == "llama3.2"
    assert explicit.selected_user_model_contract_id == contract.id
    assert explicit.user_model_contract_hash
    assert explicit.data_not_authority is True
    assert explicit.can_execute is False
    assert explicit.can_grant_authority is False

    assert catalog_groq.provider_id == "groq"
    assert catalog_groq.backend_id == "groq_openai_compatible_chat"
    assert catalog_groq.model_id == "openai/gpt-oss-20b"
    assert catalog_groq.provider_catalog_ref_hash
    assert runtime.store.verify_timeline(mission_id)


def test_hardware_snapshot_is_safe_local_and_hash_bound(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)

    snapshot = runtime.capture_hardware_snapshot(mission_id=mission_id, route_id="route_hw")

    assert snapshot.cpu_count >= 1
    assert snapshot.platform_system
    assert snapshot.hardware_probe_result.read_only is True
    assert snapshot.hardware_probe_result.network_scan_attempted is False
    assert snapshot.hardware_probe_result.credential_probe_attempted is False
    assert snapshot.verify_hash()
    assert "sk-" not in str(snapshot.safe_model_dump()).lower()


def test_runtime_probe_uses_only_explicit_loopback_endpoint_and_does_not_probe_remote(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)

    with _loopback_server() as endpoint:
        local_candidate = _local_candidate(endpoint=endpoint)
        probe = runtime.probe_runtime_availability(
            mission_id=mission_id,
            route_id="route_probe",
            candidate=local_candidate,
        )

    remote_candidate = _cloud_candidate(provider_id="remote", backend_id="remote_chat", model="remote-model")
    remote_probe = runtime.probe_runtime_availability(
        mission_id=mission_id,
        route_id="route_probe",
        candidate=remote_candidate,
    )

    assert probe.status is RuntimeProbeStatus.AVAILABLE
    assert probe.endpoint_is_loopback is True
    assert probe.network_scan_attempted is False
    assert probe.config_mutation_attempted is False
    assert probe.credential_probe_attempted is False
    assert probe.verify_hash()

    assert remote_probe.status is RuntimeProbeStatus.UNKNOWN
    assert remote_probe.endpoint_is_loopback is False
    assert "remote provider availability not probed" in remote_probe.safe_summary.lower()
    assert remote_probe.network_scan_attempted is False
    assert remote_probe.credential_probe_attempted is False


def test_route_simulation_scores_candidates_and_rejects_cloud_when_local_only(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    local_contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    cloud_contract = _contract(provider_id="groq", backend_id="groq_openai_compatible_chat", model="openai/gpt-oss-20b")

    request = runtime.create_route_request(
        mission_id=mission_id,
        objective=_objective(mission_id, required_context_tokens=2_000),
        policy=RoutePolicy(local_only=True, cloud_allowed=False, operator_confirmation_required=True),
        user_model_contract=local_contract,
        explicit_contract_candidates=[cloud_contract],
    )
    simulation = runtime.simulate_route(request)
    decision = runtime.decide_route(simulation)

    rejected = {
        score.candidate_id: [reason.code for reason in score.rejection_reasons]
        for score in simulation.candidate_scores
    }
    selected = next(score for score in simulation.candidate_scores if score.candidate_id == decision.selected_candidate_id)

    assert selected.provider_id == "ollama"
    assert selected.overall_score > 0
    assert any("local_only" in reason for reasons in rejected.values() for reason in reasons)
    assert decision.requires_operator_approval is True
    assert decision.can_execute is False
    assert decision.route_receipt_ref


def test_route_policy_enforces_cost_latency_and_allowed_blocked_identity_constraints(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    high_cost = _contract(
        provider_id="groq",
        backend_id="groq_openai_compatible_chat",
        model="openai/gpt-oss-20b",
        input_cost=50.0,
        output_cost=80.0,
    )
    low_cost = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2", input_cost=0.0, output_cost=0.0)

    request = runtime.create_route_request(
        mission_id=mission_id,
        objective=_objective(mission_id, required_context_tokens=4_000),
        policy=RoutePolicy(
            max_estimated_cost_usd=0.001,
            max_estimated_latency_seconds=5.0,
            allowed_provider_ids=["ollama", "groq"],
            blocked_model_ids=["openai/gpt-oss-20b"],
        ),
        user_model_contract=low_cost,
        explicit_contract_candidates=[high_cost],
    )
    simulation = runtime.simulate_route(request)

    groq_score = next(score for score in simulation.candidate_scores if score.provider_id == "groq")
    ollama_score = next(score for score in simulation.candidate_scores if score.provider_id == "ollama")

    assert "blocked_model" in {reason.code for reason in groq_score.rejection_reasons}
    assert "max_estimated_cost" in {reason.code for reason in groq_score.rejection_reasons}
    assert ollama_score.rejection_reasons == []
    assert simulation.selected_candidate_id == ollama_score.candidate_id


def test_route_approval_is_required_before_explicit_user_model_contract_binding(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=True)

    with pytest.raises(ModelRouterRuntimeError, match="operator approval required"):
        runtime.bind_user_model_contract(decision, user_model_contract=contract)

    approval = runtime.record_route_approval(
        decision,
        approved_by="operator_youcef",
        approval_source="operator",
        safe_summary="Operator explicitly approved the route.",
    )
    binding = runtime.bind_user_model_contract(decision, user_model_contract=contract, approval_record=approval)
    receipt = runtime.create_route_receipt(decision, approval_record=approval, binding=binding)

    assert binding.user_model_contract.selected_provider_id == "ollama"
    assert binding.selected_provider_id == "ollama"
    assert binding.selected_backend_id == "ollama_openai_compatible_chat"
    assert binding.selected_model_id == "llama3.2"
    assert binding.verify_hash()
    assert receipt.operator_approval_ref == approval.approval_id
    assert receipt.user_model_contract_binding_hash == binding.binding_hash
    assert receipt.verify_hash()


@pytest.mark.parametrize("source", ["memory", "skill", "worker", "daemon", "scheduler", "harness"])
def test_memory_skill_worker_daemon_scheduler_and_harness_cannot_trigger_model_switch(
    tmp_path: Path,
    source: str,
) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=True)

    with pytest.raises(ModelRouterRuntimeError, match="operator approval source"):
        runtime.record_route_approval(
            decision,
            approved_by=f"{source}_context",
            approval_source=source,
            safe_summary=f"{source} tried to approve a model route.",
        )


def test_router_rejects_model_override_fallback_auto_provider_native_tools_and_sensitive_persistence(
    tmp_path: Path,
) -> None:
    runtime, mission_id = _runtime(tmp_path)

    with pytest.raises(ValueError, match="provider-native tools"):
        _local_candidate(metadata={"provider_native_tools": True})

    with pytest.raises(ValueError, match="fallback"):
        _local_candidate(metadata={"fallback_provider_id": "openrouter"})

    with pytest.raises(ValueError, match="raw prompt"):
        _local_candidate(metadata={"raw_prompt": "please persist this"})

    with pytest.raises(ValueError, match="provider key"):
        _local_candidate(metadata={"provider_key": "provider-token-placeholder"})

    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=False)
    wrong_contract = _contract(provider_id="groq", backend_id="groq_openai_compatible_chat", model="openai/gpt-oss-20b")

    with pytest.raises(ModelRouterRuntimeError, match="selected UserModelContract identity mismatch"):
        runtime.bind_user_model_contract(decision, user_model_contract=wrong_contract)

    route_dir_text = "\n".join(path.read_text(encoding="utf-8") for path in runtime.route_root(mission_id, decision.route_id).rglob("*.json"))
    forbidden = ["provider_key", "raw_prompt", "raw_provider_response", "raw_reasoning", "provider-token-placeholder"]
    assert all(item not in route_dir_text for item in forbidden)


def test_route_receipt_is_hash_bound_and_cannot_be_future_permission(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=False)
    receipt = runtime.load_route_receipt(mission_id, decision.route_id)

    assert receipt.receipt_hash == decision.route_receipt_hash
    assert receipt.verify_hash()
    assert receipt.data_not_authority is True
    assert receipt.can_grant_authority is False
    assert receipt.can_execute is False

    payload = receipt.model_dump(mode="json")
    payload["authority_effect"] = "future_permission"
    with pytest.raises(ValueError):
        type(receipt).model_validate(payload)


def test_router_records_telemetry_events_and_metrics(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=False)

    snapshot = runtime.store.telemetry_sink.store.snapshot()
    events = snapshot.event_counts_by_kind
    metrics = snapshot.metric_counts_by_kind

    assert events[TelemetryEventKind.MODEL_ROUTER_CANDIDATE_REGISTERED.value] >= 1
    assert events[TelemetryEventKind.MODEL_ROUTER_HARDWARE_SNAPSHOT_CREATED.value] >= 1
    assert events[TelemetryEventKind.MODEL_ROUTER_SIMULATION_COMPLETED.value] >= 1
    assert events[TelemetryEventKind.MODEL_ROUTER_DECISION_CREATED.value] >= 1

    assert metrics[TelemetryMetricKind.MODEL_ROUTER_CANDIDATE_COUNT.value] >= 1
    assert metrics[TelemetryMetricKind.MODEL_ROUTER_CONTEXT_FIT_SCORE.value] >= 1
    assert metrics[TelemetryMetricKind.MODEL_ROUTER_PRIVACY_SCORE.value] >= 1
    assert metrics[TelemetryMetricKind.MODEL_ROUTER_QUALITY_SCORE.value] >= 1


def test_route_replay_reconstructs_route_without_reexecution(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=False)
    runtime.bind_user_model_contract(decision, user_model_contract=contract)
    events_before = len(runtime.store.load_events(mission_id))
    telemetry_events_before = len(runtime.store.telemetry_sink.store.load_events())

    replay = ModelRouterReplayBuilder(runtime.store).build(mission_id, route_id=decision.route_id)

    assert replay.mission_id == mission_id
    assert replay.route_id == decision.route_id
    assert replay.decision is not None
    assert replay.receipt is not None
    assert replay.receipt.verify_hash()
    assert replay.reexecuted_actions is False
    assert replay.tampered is False
    assert replay.final_selected_user_model_contract is not None
    assert replay.final_selected_user_model_contract.selected_provider_id == "ollama"
    assert len(runtime.store.load_events(mission_id)) == events_before
    assert len(runtime.store.telemetry_sink.store.load_events()) == telemetry_events_before


def test_fallback_attempt_is_blocked_and_recorded_without_binding_switch(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    contract = _contract(provider_id="ollama", backend_id="ollama_openai_compatible_chat", model="llama3.2")
    decision = _decision_for_contract(runtime, mission_id, contract, operator_confirmation_required=False)

    block = runtime.block_fallback_attempt(
        mission_id=mission_id,
        route_id=decision.route_id,
        attempted_provider_id="openrouter",
        attempted_backend_id="openrouter_chat_completions",
        attempted_model_id="deepseek/deepseek-v4-flash:free",
        safe_reason="selected candidate unavailable; fallback must become a new proposal",
    )

    assert block.event_type == "model_router_fallback_blocked"
    assert runtime.load_route_receipt(mission_id, decision.route_id).selected_candidate_id == decision.selected_candidate_id
    metric_kinds = [metric.metric_kind for metric in runtime.store.telemetry_sink.store.load_metrics()]
    assert TelemetryMetricKind.MODEL_ROUTER_FALLBACK_BLOCK_COUNT in metric_kinds


def _runtime(tmp_path: Path) -> tuple[ModelRouterRuntime, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_route",
        draft=MissionDraft(
            title="Route an explicit model",
            objective="Compare explicit model candidates before LLM operator execution.",
            constraints=["no fallback", "no provider-native tools"],
            expected_artifacts=["route receipt"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="route_mission",
            allowed_actions=["route_model"],
            forbidden_actions=["fallback", "provider_override"],
            summary="Model routing is proposal and binding data only.",
        ),
    )
    return ModelRouterRuntime(store=kernel.store, config=ModelRouterConfig()), record.mission_id


def _decision_for_contract(
    runtime: ModelRouterRuntime,
    mission_id: str,
    contract: UserModelContract,
    *,
    operator_confirmation_required: bool,
):
    request = runtime.create_route_request(
        mission_id=mission_id,
        objective=_objective(mission_id),
        policy=RoutePolicy(operator_confirmation_required=operator_confirmation_required),
        user_model_contract=contract,
    )
    simulation = runtime.simulate_route(request)
    return runtime.decide_route(simulation)


def _objective(mission_id: str, *, required_context_tokens: int = 1_000) -> RouteObjective:
    return RouteObjective(
        mission_id=mission_id,
        task_summary="Choose an explicit model contract for the operator cockpit.",
        required_context_tokens=required_context_tokens,
        quality_goal="operator-ready structured reasoning",
        privacy_goal="prefer local when feasible",
    )


def _contract(
    *,
    provider_id: str,
    backend_id: str,
    model: str,
    input_cost: float = 0.0,
    output_cost: float = 0.0,
) -> UserModelContract:
    return UserModelContract(
        selected_provider_id=provider_id,
        selected_backend_id=backend_id,
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=input_cost,
            output_usd_per_1m=output_cost,
            context_window_tokens=16_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=16_000,
            supports_tool_calling=False,
            strengths=["structured JSON", "operator dialogue"],
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=1_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="operator_route_v1",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _local_candidate(*, endpoint: str = "http://127.0.0.1:11434/v1/chat/completions", metadata: dict | None = None) -> ModelCandidate:
    return ModelCandidate(
        source=ModelCandidateSource.LOCAL_RUNTIME_DESCRIPTOR,
        runtime_kind=ModelRuntimeKind.OLLAMA,
        backend_kind=ModelBackendKind.OPENAI_COMPATIBLE_CHAT,
        provider_id="ollama",
        backend_id="ollama_openai_compatible_chat",
        model_id="llama3.2",
        display_name="Ollama llama3.2",
        runtime_endpoint=endpoint,
        cost_profile=ModelCostProfile(
            model_name="llama3.2",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=8_192,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="llama3.2",
            context_window_tokens=8_192,
            supports_tool_calling=False,
        ),
        context_window_profile=ModelContextWindowProfile(candidate_context_window_tokens=8_192),
        privacy_profile=ModelPrivacyProfile(local_only=True, cloud_provider=False, privacy_score=1.0),
        energy_profile=ModelEnergyProfile(energy_estimate_status="unknown"),
        metadata=metadata or {},
    ).with_hash()


def _cloud_candidate(*, provider_id: str, backend_id: str, model: str) -> ModelCandidate:
    return ModelCandidate(
        source=ModelCandidateSource.API_DESCRIPTOR,
        runtime_kind=ModelRuntimeKind.OPENAI_COMPATIBLE,
        backend_kind=ModelBackendKind.OPENAI_COMPATIBLE_CHAT,
        provider_id=provider_id,
        backend_id=backend_id,
        model_id=model,
        display_name=f"{provider_id} {model}",
        runtime_endpoint="https://example.invalid/v1/chat/completions",
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=32_000,
            supports_tool_calling=False,
        ),
        context_window_profile=ModelContextWindowProfile(candidate_context_window_tokens=32_000),
        privacy_profile=ModelPrivacyProfile(local_only=False, cloud_provider=True, privacy_score=0.45),
        energy_profile=ModelEnergyProfile(energy_estimate_status="unknown"),
    ).with_hash()


@contextmanager
def _loopback_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/v1/chat/completions"
    finally:
        server.shutdown()
        server.server_close()
