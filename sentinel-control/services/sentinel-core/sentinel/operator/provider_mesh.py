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
    ) -> None:
        if not providers:
            raise ValueError("provider mesh requires at least one explicit provider")
        self.providers = tuple(providers)
        self.fallback_order = tuple(fallback_order)
        self.retry_after_seconds = max(0, int(retry_after_seconds))
        self._active_index = 0
        self._circuit_breakers: dict[str, str] = {}
        self.safe_transitions: list[dict[str, Any]] = []
        self.call_count = 0
        self.last_actual_provider_model = self.providers[0].identity

    def complete(self, request: Any) -> Any:
        spec = self._active_provider()
        self._seal_resume_state_if_needed(request=request, spec=spec)
        mesh_request = _request_for_provider(request, spec)
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


def _request_for_provider(request: Any, spec: ProviderMeshProviderSpec) -> Any:
    provider_model = f"{spec.provider_id}/{spec.model_id}"
    updates = {"provider_model": provider_model}
    if hasattr(request, "model_copy"):
        return request.model_copy(update=updates)
    if isinstance(request, dict):
        return {**request, **updates}
    return request


def _recoverable_provider_failure_code(exc: Exception) -> str:
    text = str(exc)
    for marker in (
        "provider_failure_PROVIDER_RATE_LIMIT_http_429",
        "PROVIDER_RATE_LIMIT_http_429",
        "http_429",
        "provider_failure_PROVIDER_MODEL_UNAVAILABLE_http_503",
        "PROVIDER_MODEL_UNAVAILABLE_http_503",
        "http_503",
        "provider_mesh_provider_unavailable",
    ):
        if marker in text:
            return marker
    return ""
