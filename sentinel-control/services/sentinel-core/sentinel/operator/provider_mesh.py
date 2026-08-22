from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sentinel.agent.model_execution.redaction import stable_hash


class ProviderMeshClient(Protocol):
    def complete(self, request: Any) -> Any:
        ...


@dataclass(frozen=True)
class ProviderMeshProviderSpec:
    provider_id: str
    backend_id: str
    model_id: str
    client: ProviderMeshClient
    role: str
    context_capacity_tokens: int = 0
    cost_class: str = "unknown"
    health_state: str = "healthy"

    @property
    def identity(self) -> str:
        return f"{self.provider_id}/{self.model_id}"


class ProviderMeshTurnFailed(RuntimeError):
    def __init__(self, transition: dict[str, Any]) -> None:
        self.transition = transition
        super().__init__(str(transition.get("fallback_reason") or "provider_mesh_turn_failed"))


class ProviderMesh:
    """Explicit provider mesh for resumable canonical decision turns.

    It never dispatches effects and never chooses a model outside the configured
    list. A recoverable provider outage terminalizes only the provider turn; the
    owning root mission decides whether the next cognitive turn may continue.
    """

    def __init__(
        self,
        *,
        providers: tuple[ProviderMeshProviderSpec, ...],
        fallback_order: tuple[str, ...],
        retry_after_seconds: int = 0,
        planned_handoff_after_material_actions: int | None = None,
        planned_handoff_reason: str = "planned_provider_handoff",
        planned_handoff_required_evidence_terms: tuple[str, ...] = (),
    ) -> None:
        if not providers:
            raise ValueError("provider mesh requires at least one explicit provider")
        self.providers = tuple(providers)
        self.fallback_order = tuple(fallback_order)
        self.retry_after_seconds = max(0, int(retry_after_seconds))
        self.planned_handoff_after_material_actions = (
            None if planned_handoff_after_material_actions is None else max(0, int(planned_handoff_after_material_actions))
        )
        self.planned_handoff_reason = str(planned_handoff_reason or "planned_provider_handoff")
        self.planned_handoff_required_evidence_terms = tuple(
            str(term).strip().lower() for term in planned_handoff_required_evidence_terms if str(term).strip()
        )
        self._active_index = 0
        self._circuit_breakers: dict[str, str] = {}
        self.safe_transitions: list[dict[str, Any]] = []
        self._pending_transitions: list[dict[str, Any]] = []
        self._planned_handoff_done = False
        self.call_count = 0
        self.last_actual_provider_model = self.providers[0].identity

    def complete(self, request: Any) -> Any:
        self._apply_planned_handoff_if_ready(request)
        spec = self._active_provider()
        self._seal_resume_state_if_needed(request=request, spec=spec)
        mesh_request = _request_for_provider(request, spec, transition=self._latest_transition_for(spec))
        self.last_actual_provider_model = spec.identity
        try:
            result = spec.client.complete(mesh_request)
        except Exception as exc:
            reason = _recoverable_provider_failure_code(exc)
            if not reason:
                raise
            transition = self._record_recoverable_provider_failure(
                request=request,
                spec=spec,
                failure_reason=reason,
            )
            raise ProviderMeshTurnFailed(transition) from exc
        self.call_count += 1
        return result

    def consume_pending_transitions(self) -> tuple[dict[str, Any], ...]:
        transitions = tuple(self._pending_transitions)
        self._pending_transitions.clear()
        return transitions

    def _active_provider(self) -> ProviderMeshProviderSpec:
        while self._active_index < len(self.providers):
            spec = self.providers[self._active_index]
            if self._circuit_breakers.get(spec.identity) != "open":
                return spec
            self._active_index += 1
        raise RuntimeError("provider_mesh_no_available_provider")

    def _record_recoverable_provider_failure(
        self,
        *,
        request: Any,
        spec: ProviderMeshProviderSpec,
        failure_reason: str,
    ) -> dict[str, Any]:
        self.call_count += 1
        self._circuit_breakers[spec.identity] = "open"
        next_spec = self._next_available_provider_after(spec)
        if next_spec is None:
            raise RuntimeError(f"provider_mesh_no_fallback_available:{failure_reason}")
        self._active_index = self.providers.index(next_spec)
        state = getattr(request, "canonical_state", None)
        state_hash = str(getattr(state, "state_hash", "") or "")
        receipt_refs = tuple(getattr(state, "evidence_refs", ()) or ())
        transition = {
            "transition_kind": "fallback",
            "requested_provider": spec.provider_id,
            "requested_model": spec.model_id,
            "requested_backend": spec.backend_id,
            "actual_provider": spec.provider_id,
            "actual_model": spec.model_id,
            "actual_backend": spec.backend_id,
            "next_provider": next_spec.provider_id,
            "next_model": next_spec.model_id,
            "next_backend": next_spec.backend_id,
            "fallback_reason": failure_reason,
            "retry_after_seconds": self.retry_after_seconds,
            "mission_state_hash": state_hash,
            "previous_receipt_root": stable_hash(receipt_refs),
            "provider_turn_terminalized": True,
            "browser_actions_replayed": False,
            "fallback_silent": False,
            "fallback_order": list(self.fallback_order),
            "circuit_breaker_state": "open",
        }
        self.safe_transitions.append(transition)
        return transition

    def _apply_planned_handoff_if_ready(self, request: Any) -> None:
        if self._planned_handoff_done:
            return
        if self.planned_handoff_after_material_actions is None:
            return
        spec = self._active_provider()
        next_spec = self._next_available_provider_after(spec)
        if next_spec is None:
            return
        state = getattr(request, "canonical_state", None)
        material_count = int(getattr(state, "material_action_count", 0) or 0)
        if material_count < self.planned_handoff_after_material_actions:
            return
        if not self._required_evidence_terms_present(state):
            return
        transition = self._record_planned_handoff(request=request, spec=spec, next_spec=next_spec)
        self.safe_transitions.append(transition)
        self._pending_transitions.append(transition)
        self._active_index = self.providers.index(next_spec)
        self._planned_handoff_done = True

    def _record_planned_handoff(
        self,
        *,
        request: Any,
        spec: ProviderMeshProviderSpec,
        next_spec: ProviderMeshProviderSpec,
    ) -> dict[str, Any]:
        state = getattr(request, "canonical_state", None)
        state_hash = str(getattr(state, "state_hash", "") or "")
        receipt_refs = tuple(getattr(state, "evidence_refs", ()) or ())
        return {
            "transition_kind": "planned_handoff",
            "requested_provider": spec.provider_id,
            "requested_model": spec.model_id,
            "requested_backend": spec.backend_id,
            "actual_provider": spec.provider_id,
            "actual_model": spec.model_id,
            "actual_backend": spec.backend_id,
            "next_provider": next_spec.provider_id,
            "next_model": next_spec.model_id,
            "next_backend": next_spec.backend_id,
            "handoff_reason": self.planned_handoff_reason,
            "mission_state_hash": state_hash,
            "previous_receipt_root": stable_hash(receipt_refs),
            "provider_turn_terminalized": False,
            "browser_actions_replayed": False,
            "fallback_silent": False,
            "fallback_order": list(self.fallback_order),
            "circuit_breaker_state": "unchanged",
        }

    def _required_evidence_terms_present(self, state: Any) -> bool:
        if not self.planned_handoff_required_evidence_terms:
            return True
        haystack = str(
            {
                "evidence_refs": tuple(getattr(state, "evidence_refs", ()) or ()),
                "recent_observations": tuple(getattr(state, "recent_observations", ()) or ()),
            }
        ).lower()
        return all(term in haystack for term in self.planned_handoff_required_evidence_terms)

    def _seal_resume_state_if_needed(self, *, request: Any, spec: ProviderMeshProviderSpec) -> None:
        if not self.safe_transitions:
            return
        transition = self.safe_transitions[-1]
        if transition.get("next_provider") != spec.provider_id or transition.get("next_model") != spec.model_id:
            return
        state = getattr(request, "canonical_state", None)
        state_hash = str(getattr(state, "state_hash", "") or "")
        if state_hash:
            transition["mission_state_hash"] = state_hash

    def _next_available_provider_after(self, spec: ProviderMeshProviderSpec) -> ProviderMeshProviderSpec | None:
        current_rank = self._rank(spec.model_id)
        ordered = sorted(
            enumerate(self.providers),
            key=lambda item: (self._rank(item[1].model_id), item[0]),
        )
        for _, candidate in ordered:
            if candidate is spec:
                continue
            if self._rank(candidate.model_id) <= current_rank:
                continue
            if self._circuit_breakers.get(candidate.identity) == "open":
                continue
            return candidate
        return None

    def _rank(self, model_id: str) -> int:
        try:
            return self.fallback_order.index(model_id)
        except ValueError:
            return len(self.fallback_order) + 1

    def _latest_transition_for(self, spec: ProviderMeshProviderSpec) -> dict[str, Any] | None:
        if not self.safe_transitions:
            return None
        transition = self.safe_transitions[-1]
        if transition.get("next_provider") != spec.provider_id or transition.get("next_model") != spec.model_id:
            return None
        return transition


def _request_for_provider(request: Any, spec: ProviderMeshProviderSpec, *, transition: dict[str, Any] | None = None) -> Any:
    provider_model = f"{spec.provider_id}/{spec.model_id}"
    updates = {"provider_model": provider_model}
    if transition is not None:
        state = getattr(request, "canonical_state", None)
        if state is not None and hasattr(state, "model_copy"):
            observations = tuple(getattr(state, "recent_observations", ()) or ())
            state = state.model_copy(
                update={
                    "recent_observations": (
                        *observations,
                        _model_visible_handoff_observation(transition),
                    )
                }
            )
            updates["canonical_state"] = state
    if hasattr(request, "model_copy"):
        return request.model_copy(update=updates)
    if isinstance(request, dict):
        return {**request, **updates}
    return request


def _model_visible_handoff_observation(transition: dict[str, Any]) -> dict[str, Any]:
    transition_kind = str(transition.get("transition_kind") or "")
    provider_handoff = "fallback" if transition_kind == "fallback" or transition.get("fallback_reason") else "planned"
    return {
        "provider_handoff": provider_handoff,
        "previous_provider": transition.get("actual_provider"),
        "previous_model": transition.get("actual_model"),
        "next_provider": transition.get("next_provider"),
        "next_model": transition.get("next_model"),
        "handoff_reason": transition.get("handoff_reason") or transition.get("fallback_reason"),
        "mission_state_hash": transition.get("mission_state_hash"),
        "previous_receipt_root": transition.get("previous_receipt_root"),
        "browser_actions_replayed": False,
        "data_not_authority": True,
        "can_execute": False,
    }


def _recoverable_provider_failure_code(exc: Exception) -> str:
    text = str(exc)
    for marker in (
        "provider_failure_PROVIDER_RATE_LIMIT_http_429",
        "PROVIDER_RATE_LIMIT_http_429",
        "http_429",
        "provider_failure_PROVIDER_AUTH_ERROR_credential_rejected_http_401",
        "provider_failure_PROVIDER_AUTH_ERROR_http_401",
        "PROVIDER_AUTH_ERROR_credential_rejected_http_401",
        "PROVIDER_AUTH_ERROR_http_401",
        "http_401",
        "provider_failure_PROVIDER_MODEL_UNAVAILABLE_http_503",
        "PROVIDER_MODEL_UNAVAILABLE_http_503",
        "http_503",
        "provider_mesh_provider_unavailable",
    ):
        if marker in text:
            return marker
    return ""
