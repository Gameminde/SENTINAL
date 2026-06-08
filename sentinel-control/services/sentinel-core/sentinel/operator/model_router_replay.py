from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.model_router_models import (
    HardwareInventorySnapshot,
    ModelCandidate,
    RouteApprovalRecord,
    RouteDecision,
    RouteDecisionReceipt,
    RouteExecutionBinding,
    RoutePolicy,
    RouteReplayView,
    RouteSimulationResult,
    RuntimeAvailabilityProbe,
)
from sentinel.operator.store import MissionRunStore


class ModelRouterReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str, *, route_id: str) -> RouteReplayView:
        root = self._route_root(mission_id, route_id)
        candidates = _load_many(root / "candidates", ModelCandidate)
        probes = _load_many(root / "runtime_probes", RuntimeAvailabilityProbe)
        snapshot = _load_one(root / "hardware_snapshot.json", HardwareInventorySnapshot)
        simulation = _load_one(root / "simulation.json", RouteSimulationResult)
        decision = _load_one(root / "decision.json", RouteDecision)
        receipt = _load_one(root / "receipt.json", RouteDecisionReceipt)
        approval = _load_one(root / "approval.json", RouteApprovalRecord)
        binding = _load_one(root / "binding.json", RouteExecutionBinding)
        route_policy = None
        if simulation is not None and decision is not None:
            # The replay view keeps the policy hash in the decision. The full
            # policy is available in request.json, loaded best-effort below.
            request = _read_json_model(root / "request.json")
            if request and isinstance(request.get("policy"), dict):
                route_policy = RoutePolicy.model_validate(request["policy"])

        tampered = not self._store.verify_timeline(mission_id)
        tampered = tampered or any(not item.verify_hash() for item in candidates)
        tampered = tampered or any(not item.verify_hash() for item in probes)
        for item in (snapshot, simulation, decision, receipt, approval, binding):
            if item is not None and hasattr(item, "verify_hash") and not item.verify_hash():
                tampered = True

        route_events = [
            event
            for event in self._store.load_events(mission_id)
            if event.event_type.startswith("model_router_") and event.metadata.get("route_id") == route_id
        ]
        return RouteReplayView(
            mission_id=mission_id,
            route_id=route_id,
            candidates=candidates,
            hardware_snapshot=snapshot,
            runtime_probes=probes,
            route_policy=route_policy,
            simulation=simulation,
            decision=decision,
            receipt=receipt,
            approval_record=approval,
            binding_record=binding,
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in route_events)),
            memory_feedback_refs=[],
            final_selected_user_model_contract=binding.user_model_contract if binding else None,
            tampered=tampered,
            reexecuted_actions=False,
        )

    def _route_root(self, mission_id: str, route_id: str) -> Path:
        return self._store.mission_dir(mission_id) / "model_router" / stable_hash(route_id)[:24]


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


def _load_one(path: Path, model: Any) -> Any | None:
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _read_json_model(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    import json

    return json.loads(path.read_text(encoding="utf-8"))
