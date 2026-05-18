from __future__ import annotations

from typing import Any

from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.catalog import ProviderCatalog, ProviderCatalogStatus
from sentinel.agent.model_execution.credentials import CredentialResolution, ProviderCredentialHandle
from sentinel.agent.model_execution.models import ModelExecutionOutcome, ModelExecutionOutcomeClass, RealModelRequest
from sentinel.agent.model_execution.policy import ModelExecutionBudgetPolicy, ModelRetryPolicy, ModelTimeoutPolicy
from sentinel.agent.model_execution.receipts import build_model_execution_receipt
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.agent.model_execution.registry import ModelProviderRegistry
from sentinel.agent.model_execution.validator import LLMDecisionResultValidator
from sentinel.perf.caches.model_call_optimizer import ModelCallPlan


class RealModelRequestBuilder:
    @staticmethod
    def build(
        *,
        frame: LLMDecisionFrame,
        rendered_prompt: str,
        plan: ModelCallPlan,
        user_model: UserModelContract,
        timeout_policy: ModelTimeoutPolicy,
        retry_policy: ModelRetryPolicy,
        budget_policy: ModelExecutionBudgetPolicy,
    ) -> RealModelRequest:
        if plan.model_id != user_model.selected_model:
            raise ValueError("ModelCallPlan cannot override the user-selected model.")
        if plan.provider_id != user_model.selected_provider_id:
            raise ValueError("ModelCallPlan provider_id must match the user-selected provider.")
        if plan.backend_id != user_model.selected_backend_id:
            raise ValueError("ModelCallPlan backend_id must match the user-selected backend.")
        prompt_hash = text_hash(rendered_prompt)
        metadata = {
            "plan_rationale": plan.rationale,
            "provider_id": plan.provider_id,
            "backend_id": plan.backend_id,
            "use_prefix_reuse": plan.use_prefix_reuse,
            "stable_prefix_hash": plan.stable_prefix_hash,
            "evidence_delta_count": plan.evidence_delta_count,
            "frame_evidence_refs": [
                str(ref)
                for card in frame.top_k_evidence
                for ref in getattr(card, "evidence_refs", [])
            ],
            "frame_receipt_refs": list(frame.receipt_refs),
        }
        hash_payload = {
            "provider_id": plan.provider_id,
            "model_id": plan.model_id,
            "backend_id": plan.backend_id,
            "backend": plan.backend_id,
            "runtime": plan.runtime,
            "prompt_hash": prompt_hash,
            "frame_hash": frame.frame_hash,
            "user_model_contract_id": user_model.id,
            "estimated_input_tokens": plan.estimated_input_tokens,
            "estimated_output_tokens": user_model.context_budget_policy.reserve_output_tokens,
            "request_metadata": metadata,
            "timeout_policy_id": timeout_policy.id,
            "retry_policy_id": retry_policy.id,
            "budget_policy_id": budget_policy.id,
        }
        return RealModelRequest(
            provider_id=plan.provider_id,
            model_id=plan.model_id,
            backend_id=plan.backend_id,
            backend=plan.backend_id,
            runtime=plan.runtime,
            prompt_hash=prompt_hash,
            frame_hash=frame.frame_hash,
            user_model_contract_id=user_model.id,
            estimated_input_tokens=plan.estimated_input_tokens,
            estimated_output_tokens=user_model.context_budget_policy.reserve_output_tokens,
            prompt_text_in_memory_only=rendered_prompt,
            request_metadata=metadata,
            timeout_policy_id=timeout_policy.id,
            retry_policy_id=retry_policy.id,
            budget_policy_id=budget_policy.id,
            request_hash=stable_hash(hash_payload),
        )


class ModelExecutionCoordinator:
    def __init__(
        self,
        *,
        registry: ModelProviderRegistry | None = None,
        credential_resolver: Any | None = None,
        timeout_policy: ModelTimeoutPolicy | None = None,
        provider_catalog: ProviderCatalog | None = None,
        enabled_provider_ids: set[str] | frozenset[str] | None = None,
        allow_diagnostic_provider_ids: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._registry = registry
        self._credential_resolver = credential_resolver
        self._timeout_policy = timeout_policy or ModelTimeoutPolicy(
            connect_timeout_seconds=2.0,
            read_timeout_seconds=5.0,
            total_timeout_seconds=7.0,
        )
        self._provider_catalog = provider_catalog
        self._enabled_provider_ids = frozenset(enabled_provider_ids) if enabled_provider_ids is not None else None
        self._allow_diagnostic_provider_ids = frozenset(allow_diagnostic_provider_ids or ())

    def execute(self, *, request: RealModelRequest) -> ModelExecutionOutcome:
        if self._registry is None:
            return ModelExecutionOutcome(
                outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND,
                success=False,
                message="model execution coordinator is default-off",
            )
        catalog_outcome = self._catalog_gate(request)
        if catalog_outcome is not None:
            return catalog_outcome
        try:
            provider = self._registry.get_enabled(request.provider_id, model_id=request.model_id)
        except LookupError:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.UNKNOWN_PROVIDER, success=False)
        except PermissionError:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND, success=False)

        if self._credential_resolver is None:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.MISSING_CREDENTIAL, success=False)
        credential = self._resolve_credential(request.provider_id)
        if credential is None:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.MISSING_CREDENTIAL, success=False)
        if credential.provider_id != request.provider_id:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.MISSING_CREDENTIAL, success=False)

        response = provider.execute(request, timeout=self._timeout_policy, credential=credential)
        if response is None:
            return ModelExecutionOutcome(
                outcome_class=ModelExecutionOutcomeClass.MODEL_EXECUTION_DEFERRED,
                success=False,
                provider_called=True,
                message="Pack A does not accept fake success or real provider success without Wave 8.",
            )
        allowed_refs: set[str] = set()
        for key in ("frame_receipt_refs", "frame_evidence_refs"):
            values = request.request_metadata.get(key)
            if isinstance(values, list):
                allowed_refs.update(str(ref) for ref in values)
        allowed_evidence_refs = allowed_refs or None
        result = LLMDecisionResultValidator.validate(response, allowed_evidence_refs=allowed_evidence_refs)
        receipt = build_model_execution_receipt(
            request=request,
            outcome_class=result.outcome_class,
            result=result,
            credential=credential,
            attempts=1,
        )
        return ModelExecutionOutcome(
            outcome_class=result.outcome_class,
            success=result.success,
            result=result,
            receipt=receipt,
            provider_called=True,
        )

    def _resolve_credential(self, provider_id: str) -> ProviderCredentialHandle | None:
        resolved = self._credential_resolver.resolve(provider_id=provider_id, required_scopes=["model:read"])
        if isinstance(resolved, CredentialResolution):
            return resolved.credential if resolved.outcome_class is ModelExecutionOutcomeClass.SUCCESS_VALIDATED else None
        if isinstance(resolved, ProviderCredentialHandle):
            return resolved
        return None

    def _catalog_gate(self, request: RealModelRequest) -> ModelExecutionOutcome | None:
        if self._provider_catalog is None:
            return None
        try:
            entry = self._provider_catalog.get(request.provider_id)
        except LookupError:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.UNKNOWN_PROVIDER, success=False)
        if self._enabled_provider_ids is not None and request.provider_id not in self._enabled_provider_ids:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND, success=False)
        if entry.status is ProviderCatalogStatus.DISABLED:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND, success=False)
        if entry.status is ProviderCatalogStatus.DIAGNOSTIC and request.provider_id not in self._allow_diagnostic_provider_ids:
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND, success=False)
        backend = next((candidate for candidate in entry.backends if candidate.backend_id == request.backend_id), None)
        if backend is None or not backend.supports_model(request.model_id):
            return ModelExecutionOutcome(outcome_class=ModelExecutionOutcomeClass.DISABLED_BACKEND, success=False)
        return None
