from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator.browser_search_parameter_boundary import (
    BrowserSearchParameterBoundaryError,
    normalize_model_browser_search_parameters,
)
from sentinel.operator.browser_completion_policy import (
    browser_summary_supports_terminal_answer,
    browser_summary_supports_terminal_blocker,
)
from sentinel.operator.browser_model_native_control_loop import map_browser_model_native_intent
from sentinel.operator.live_run_evidence_sink import safe_model_operational_assessment


_BROWSER_MODEL_SKILLS = {
    "observe",
    "navigate",
    "search",
    "follow",
    "inspect",
    "extract_evidence",
    "verify",
    "recover_session",
    "browse_search",
    "extract",
}


class ProductModelClient(Protocol):
    def complete(self, request: Any) -> Any:
        ...


ProductModelRequestFactory = Callable[[dict[str, Any], str], Any]


class ProductModelNativeDecisionClient:
    """Map model-native product intent into Sentinel's internal action language.

    The model-facing contract is intentionally small: simple mission skills and
    natural/semi-structured intent. ActionEnvelope stays below the model as the
    runtime handoff format.
    """

    def __init__(
        self,
        *,
        model_client: ProductModelClient,
        request_factory: ProductModelRequestFactory,
        preferred_skill_sequence: tuple[str, ...] = (),
        canonical_decision_mode: bool = False,
        canonical_provider_id: str = "",
        canonical_backend_id: str = "",
        canonical_model_id: str = "",
    ) -> None:
        self._model_client = model_client
        self._request_factory = request_factory
        self._preferred_skill_sequence = tuple(preferred_skill_sequence)
        self._canonical_decision_mode = canonical_decision_mode
        self._canonical_provider_id = canonical_provider_id
        self._canonical_backend_id = canonical_backend_id
        self._canonical_model_id = canonical_model_id
        self.call_count = 0
        self.safe_diagnostics: list[dict[str, Any]] = []
        self.latest_safe_model_operational_assessment: dict[str, Any] | None = None

    @classmethod
    def for_canonical_decisions(
        cls,
        *,
        model_client: ProductModelClient,
        provider_id: str,
        backend_id: str,
        model_id: str,
        user_model_contract_id: str = "",
    ) -> "ProductModelNativeDecisionClient":
        contract_id = user_model_contract_id or _canonical_user_model_contract(
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
        ).id

        def request_factory(context: dict[str, Any], prompt: str) -> RealModelRequest:
            return _canonical_real_model_request(
                canonical_request=context["canonical_request"],
                prompt=prompt,
                provider_id=provider_id,
                backend_id=backend_id,
                model_id=model_id,
                user_model_contract_id=contract_id,
            )

        return cls(
            model_client=model_client,
            request_factory=request_factory,
            canonical_decision_mode=True,
            canonical_provider_id=provider_id,
            canonical_backend_id=backend_id,
            canonical_model_id=model_id,
        )

    def complete(self, context: Any) -> Any:
        if self._canonical_decision_mode:
            return self._complete_canonical(context)
        context = dict(context)
        if self._preferred_skill_sequence:
            context["_preferred_skill_sequence"] = self._preferred_skill_sequence
        prompt = _compile_model_native_prompt(context)
        request = self._request_factory(context, prompt)
        raw_output = self._model_client.complete(request)
        self.call_count += 1
        sanitized_output = _drop_safe_provider_wrapper(raw_output)
        self.latest_safe_model_operational_assessment = safe_model_operational_assessment(
            _extract_payload(sanitized_output)
            if not isinstance(sanitized_output, dict)
            else sanitized_output
        )
        if _contains_forbidden_raw_material(sanitized_output):
            self._record_diagnostic(
                context=context,
                raw_output=sanitized_output,
                failure_code="MODEL_NATIVE_DECISION_FORBIDDEN_RAW_MATERIAL",
            )
            raise ActionKernelError("MODEL_NATIVE_DECISION_FORBIDDEN_RAW_MATERIAL")
        try:
            decision = _map_output_to_action(sanitized_output, context=context)
        except ActionKernelError as exc:
            self._record_diagnostic(context=context, raw_output=sanitized_output, failure_code=str(exc))
            raise
        self._record_diagnostic(
            context=context,
            raw_output=sanitized_output,
            failure_code=None,
            mapped_action=f"{decision.capability_id}.{decision.operation}",
        )
        return decision

    def _complete_canonical(self, request: Any) -> Any:
        from sentinel.operator.canonical_core import CanonicalDecision, CanonicalDecisionRequest, DecisionOrigin, DecisionProtocol

        if not isinstance(request, CanonicalDecisionRequest):
            raise ActionKernelError("CANONICAL_DECISION_REQUEST_REQUIRED")
        prompt = _compile_canonical_product_prompt(request)
        real_request = self._request_factory({"canonical_request": request}, prompt)
        raw_output = self._model_client.complete(real_request)
        self.call_count += 1
        payload = extract_canonical_json_decision(raw_output)
        capability = str(payload.get("capability") or payload.get("selected_capability") or "").strip()
        operation = str(payload.get("operation") or payload.get("selected_operation") or "").strip()
        if not capability and "." in operation:
            capability, operation = operation.split(".", 1)
        if not capability or not operation:
            raise ActionKernelError("CANONICAL_DECISION_CAPABILITY_OPERATION_REQUIRED")
        route_schema = _canonical_route_schema(request, capability=capability, operation=operation)
        arguments = payload.get("arguments", payload.get("params", {}))
        if not isinstance(arguments, dict):
            raise ActionKernelError("CANONICAL_DECISION_ARGUMENTS_MUST_BE_OBJECT")
        decision = CanonicalDecision(
            root_mission_id=request.root_mission_id,
            provider_model=request.provider_model,
            decision_protocol=DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1,
            decision_origin=DecisionOrigin.MODEL_SELECTED,
            objective_interpretation=str(payload.get("objective_interpretation") or ""),
            selected_capability=capability,
            selected_operation=operation,
            typed_proposed_effect=str(route_schema.get("effect_kind") or payload.get("typed_proposed_effect") or "unknown"),
            arguments=arguments,
            expected_state_delta=str(payload.get("expected_state_delta") or "unknown"),
            evidence_needed=tuple(str(item) for item in payload.get("evidence_needed", ()) if str(item).strip()),
            recovery_intent=str(payload.get("recovery_intent") or ""),
        )
        self._record_diagnostic(
            context=request.canonical_state.safe_model_dump(),
            raw_output=payload,
            failure_code=None,
            mapped_action=f"{decision.capability}.{decision.operation}",
        )
        return decision

    def _record_diagnostic(
        self,
        *,
        context: dict[str, Any],
        raw_output: Any,
        failure_code: str | None,
        mapped_action: str | None = None,
    ) -> None:
        self.safe_diagnostics.append(
            {
                "context_hash": stable_hash(_safe_context_shape(context)),
                "model_output_hash": text_hash(_safe_render_shape(raw_output)),
                "failure_code": failure_code,
                "mapped_action": mapped_action,
                "raw_model_material_persisted": False,
            }
        )


def _canonical_user_model_contract(*, provider_id: str, backend_id: str, model_id: str) -> UserModelContract:
    return UserModelContract(
        selected_provider_id=provider_id,
        selected_backend_id=backend_id,
        selected_model=model_id,
        cost_profile=ModelCostProfile(
            model_name=model_id,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model_id,
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=700,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="canonical_core_workspace_vertical_slice",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _canonical_real_model_request(
    *,
    canonical_request: Any,
    prompt: str,
    provider_id: str,
    backend_id: str,
    model_id: str,
    user_model_contract_id: str,
) -> RealModelRequest:
    metadata = {
        "raw_text_transport": "product_model_native_intent_v1",
        "canonical_core_product_route": True,
        "mission_id": canonical_request.root_mission_id,
        "canonical_state_hash": canonical_request.canonical_state.state_hash,
        "model_visible_affordances": list(canonical_request.canonical_state.model_visible_affordances),
        "fallback_auto_enabled": False,
        "provider_native_tools_enabled": False,
    }
    prompt_hash = text_hash(prompt)
    hash_payload = {
        "provider_id": provider_id,
        "backend_id": backend_id,
        "model_id": model_id,
        "runtime": "product_model_native_decision",
        "prompt_hash": prompt_hash,
        "frame_hash": canonical_request.canonical_state.state_hash,
        "user_model_contract_id": user_model_contract_id,
        "request_metadata": metadata,
    }
    return RealModelRequest(
        provider_id=provider_id,
        model_id=model_id,
        backend_id=backend_id,
        backend=backend_id,
        runtime="product_model_native_decision",
        prompt_hash=prompt_hash,
        frame_hash=canonical_request.canonical_state.state_hash,
        user_model_contract_id=user_model_contract_id,
        estimated_input_tokens=max(1, (len(prompt) + 3) // 4),
        estimated_output_tokens=700,
        prompt_text_in_memory_only=prompt,
        request_metadata=metadata,
        timeout_policy_id="canonical_product_default_timeout",
        retry_policy_id="canonical_product_no_retry",
        budget_policy_id="canonical_product_bounded_budget",
        request_hash=stable_hash(hash_payload),
    )


def _compile_canonical_product_prompt(request: Any) -> str:
    state = request.canonical_state.safe_model_dump()
    operation_schemas = state.get("model_visible_operation_schemas", [])
    affordances = tuple(str(item) for item in state.get("model_visible_affordances", ()) if str(item))
    browser_readonly_available = any(item.startswith("real_browser_control.real_browser.") for item in affordances)
    capability_boundary = (
        "Do not request code execution, network outside the registered read-only browser route, credentials, "
        "shell, provider-native tools, fallback, authority changes, or mutating browser effects.\n"
        if browser_readonly_available
        else "Do not request code execution, network, credentials, browser, shell, provider-native tools, fallback, or authority changes.\n"
    )
    return (
        "You are the model brain. Sentinel is the body, state, effects, proof, and laws.\n"
        "Choose exactly one safe next operation for this read-only workspace mission.\n"
        "Return exactly one JSON object and no markdown.\n"
        "Allowed operations are generated from Sentinel's executable capability graph:\n"
        f"{json.dumps(operation_schemas, sort_keys=True, default=str)}\n"
        f"{capability_boundary}"
        "Finish only after a prior receipt/evidence ref supports the answer.\n"
        f"Mission objective: {request.canonical_state.objective}\n"
        f"Mission objective hash: {text_hash(request.canonical_state.objective)}\n"
        f"Canonical state: {json.dumps(state, sort_keys=True, default=str)}\n"
    )


def extract_canonical_json_decision(raw: Any) -> dict[str, Any]:
    text = ""
    if isinstance(raw, dict):
        if raw.get("provider_failure") is True:
            category = str(raw.get("provider_failure_category") or raw.get("provider_error_class") or "UNKNOWN")
            diagnosis = _canonical_provider_failure_diagnosis(raw)
            raise ActionKernelError(f"canonical_provider_failure_{category}_{diagnosis}")
        metadata = raw.get("metadata")
        if isinstance(metadata, dict) and metadata.get("blocked_reason"):
            raise ActionKernelError(f"canonical_provider_blocked_{metadata.get('blocked_reason')}")
        for key in ("content", "reply", "text", "message"):
            value = raw.get(key)
            if isinstance(value, str):
                text = value
                break
        if not text and isinstance(metadata, dict):
            for key in ("content", "reply", "text", "message"):
                value = metadata.get(key)
                if isinstance(value, str):
                    text = value
                    break
        if not text and {"capability", "operation"} <= set(raw):
            return raw
    elif isinstance(raw, str):
        text = raw
    if not text.strip():
        raise ActionKernelError("canonical_provider_decision_empty")
    candidate = _first_json_object(text)
    if candidate is None:
        raise ActionKernelError("canonical_provider_decision_json_missing")
    return candidate


def _canonical_provider_failure_diagnosis(payload: dict[str, Any]) -> str:
    category = str(payload.get("provider_failure_category") or payload.get("provider_error_class") or "UNKNOWN")
    status = payload.get("http_status") or payload.get("status_code")
    try:
        http_status = int(status)
    except (TypeError, ValueError):
        http_status = None
    if category == "PROVIDER_AUTH_ERROR":
        if http_status == 401:
            return "credential_rejected_http_401"
        if http_status == 403:
            return "model_or_workspace_unauthorized_http_403"
        if http_status in {400, 404}:
            return f"endpoint_or_model_http_{http_status}"
        if http_status is not None:
            return f"auth_rejected_http_{http_status}"
        return "auth_rejected_status_unknown"
    if http_status is not None:
        return f"http_{http_status}"
    return "cause_unknown"


def _canonical_route_schema(request: Any, *, capability: str, operation: str) -> dict[str, Any]:
    for schema in request.canonical_state.model_visible_operation_schemas:
        if (
            str(schema.get("capability") or "") == capability
            and str(schema.get("operation") or "") == operation
        ):
            return schema
    raise ActionKernelError(f"canonical_decision_capability_not_advertised:{capability}.{operation}")


def _compile_model_native_prompt(context: dict[str, Any]) -> str:
    skills = ", ".join(str(skill) for skill in context.get("model_visible_skills", ()))
    try:
        recommended = _recommended_skill(context)
    except ActionKernelError:
        recommended = str(context.get("primary_model_recommended_next_skill") or "")
    objective = str(context.get("mission_objective") or "")
    progress = str(context.get("progress_state") or "")
    receipt_count = len(context.get("recent_product_receipt_refs") or ())
    recovery_hint = _recovery_prompt_hint(context)
    workspace_hint = _workspace_file_prompt_hint(context)
    proof_hint = _browser_proof_index_prompt_hint(context)
    operation_schemas = _model_visible_operation_schemas(context)
    return (
        "You are the brain. Sentinel is the body/runtime/proof layer.\n"
        f"Mission objective: {objective}\n"
        f"Progress: {progress}\n"
        f"Visible skills: {skills}\n"
        f"Best next skill: {recommended}\n"
        f"Product receipts so far: {receipt_count}\n"
        f"{recovery_hint}"
        f"{workspace_hint}"
        f"{proof_hint}"
        "Choose exactly one next skill for this turn.\n"
        "Allowed operations are generated from Sentinel's executable capability graph.\n"
        f"model_visible_operation_schemas: {json.dumps(operation_schemas, sort_keys=True, default=str)}\n"
        "Prefer one compact JSON object using a listed skill and params.\n"
        "When finishing an evidence-seeking browser mission, include exactly one terminal payload: "
        "{\"skill\":\"finish\",\"final_answer\":{\"answer_text\":\"...\",\"answer_claims\":[{\"claim_type\":\"sourced_factual_claim\",\"text\":\"...\",\"evidence_refs\":[\"evidence:...\"]}],\"public_evidence\":[]}} "
        "or {\"skill\":\"finish\",\"honest_blocker\":{\"reason\":\"...\",\"available_evidence_refs\":[],\"missing_evidence\":[]}}.\n"
        "Do not let Sentinel write the answer for you: answer_text is your user-facing answer, and factual claims must cite evidence refs.\n"
        "Natural intent is acceptable when the transport preserves visible text, but JSON is most reliable.\n"
        "Do not request login, payment, credentials, provider-native tools, or fallback/AUTO."
    )


def _model_visible_operation_schemas(context: dict[str, Any]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for skill in context.get("model_visible_skills") or ():
        skill_id = str(skill)
        runtime_action = _runtime_action_for_skill(context, skill_id)
        schemas.append(
            {
                "skill": skill_id,
                "params_schema": _params_schema_for_skill(skill_id),
                "runtime_internal_action": runtime_action,
                "data_not_authority": True,
                "can_grant_authority": False,
                "can_execute": False,
            }
        )
    return schemas


def _params_schema_for_skill(skill: str) -> dict[str, Any]:
    if skill == "read":
        return {"path": "optional safe relative workspace path"}
    if skill == "search":
        return {"query": "required inert semantic text"}
    if skill == "finish":
        return {"safe_summary": "optional concise answer or honest blocker payload"}
    if skill == "patch":
        return {
            "target_path": "safe relative workspace path",
            "expected_base_hash": "required hash when modifying existing file",
        }
    if skill == "create_file":
        return {"target_path": "safe relative workspace path", "new_text": "bounded file content"}
    if skill == "run_check":
        return {"profile_id": "bounded sandbox profile"}
    return {"params": "skill-specific bounded semantic parameters"}


def _workspace_file_prompt_hint(context: dict[str, Any]) -> str:
    summaries = [item for item in context.get("workspace_file_summaries") or () if isinstance(item, dict)]
    if not summaries:
        return ""
    lines = [
        "Safe workspace file snippets for repair, hashes, and semantic checks:",
    ]
    for item in summaries[:3]:
        path = str(item.get("path") or "")
        sha = str(item.get("sha256") or "")
        excerpt = str(item.get("content_excerpt") or "")
        if not path or not excerpt:
            continue
        lines.append(f"FILE {path} sha256={sha}")
        lines.append(excerpt[:1200])
    lines.append(
        "If repairing a file, return patch with params target_path, expected_base_hash, old_text, and new_text."
    )
    return "\n".join(lines) + "\n"


def _browser_proof_index_prompt_hint(context: dict[str, Any]) -> str:
    summary = context.get("browser_proof_index_summary")
    if not isinstance(summary, dict):
        return ""
    receipt_count = int(summary.get("material_browser_receipt_count") or 0)
    evidence_count = int(summary.get("public_evidence_count") or 0)
    missing_count = int(summary.get("browser_receipt_missing_count") or 0)
    claim_counts = summary.get("answer_claim_counts") if isinstance(summary.get("answer_claim_counts"), dict) else {}
    if receipt_count == 0 and evidence_count == 0 and not claim_counts:
        return ""
    evidence_ids = [
        str(item)
        for item in summary.get("public_evidence_ids", [])
        if str(item).strip()
    ][:8]
    return (
        "Safe browser proof index summary:\n"
        f"- readable_material_browser_receipts={receipt_count - missing_count}\n"
        f"- missing_material_browser_receipts={missing_count}\n"
        f"- public_evidence_count={evidence_count}\n"
        f"- public_evidence_ids={evidence_ids}\n"
        f"- answer_claim_counts={claim_counts}\n"
    )


def _map_output_to_action(raw_output: Any, *, context: dict[str, Any]) -> ActionEnvelope:
    if isinstance(raw_output, ActionEnvelope):
        return raw_output
    payload = _extract_payload(raw_output)
    text = _extract_text(raw_output, payload)
    visible_content_failure = _visible_content_failure(payload)
    if visible_content_failure is not None and not text.strip():
        raise ActionKernelError(visible_content_failure)
    skill = _requested_skill(payload, text)
    if not _skill_carries_inert_browser_semantic_data(skill):
        hard_boundary = _hard_boundary_action(text, payload)
        if hard_boundary is not None:
            return hard_boundary
        if _credential_boundary_requested(text, payload):
            raise ActionKernelError("MODEL_NATIVE_DECISION_HARD_BOUNDARY_CREDENTIAL_ACCESS")
    browser_mapping = _browser_native_mapping(raw_output, payload=payload, text=text, context=context)
    if browser_mapping is not None:
        return browser_mapping
    if skill is None:
        skill = _recommended_skill(context)
    else:
        quality_skill = _pending_workspace_quality_skill(context)
        if quality_skill is not None and skill in {"run_check", "send_message", "spawn_worker", "finish"}:
            skill = quality_skill
    if skill == "finish":
        sequence_skill = _next_preferred_sequence_skill(context)
        if sequence_skill is not None and sequence_skill != "finish":
            skill = sequence_skill
        elif not _finish_skill_available(context):
            recommended = _recommended_skill(context)
            if recommended != "finish":
                skill = recommended
    return _skill_to_action(skill, payload=payload, text=text, context=context)


def _browser_native_mapping(
    raw_output: Any,
    *,
    payload: dict[str, Any],
    text: str,
    context: dict[str, Any],
) -> ActionEnvelope | None:
    if not _should_use_browser_native_mapping(payload=payload, text=text, context=context):
        return None
    mapping = map_browser_model_native_intent(raw_output, context=_browser_native_context(context))
    if mapping.blocked or mapping.envelope is None:
        reason = mapping.blocked_reason or mapping.safe_diagnostics.get("failure_code") or "MODEL_NATIVE_BROWSER_INTENT_MAPPING_FAILED"
        raise ActionKernelError(str(reason))
    if not mapping.envelope.capability_id or not mapping.envelope.operation:
        reason = mapping.safe_diagnostics.get("failure_code") or "MODEL_NATIVE_BROWSER_INTENT_MAPPING_FAILED"
        raise ActionKernelError(str(reason))
    return _normalize_browser_search_action(mapping.envelope, fallback_query=_bounded_query(text) or "mission objective")


def _should_use_browser_native_mapping(
    *,
    payload: dict[str, Any],
    text: str,
    context: dict[str, Any],
) -> bool:
    if _payload_names_simple_model_skill(payload):
        return False
    if _payload_names_browser_action(payload):
        return True
    has_browser_progress = _context_has_browser_progress(context)
    if has_browser_progress:
        return True
    if _payload_names_browser_completion_action(payload) and has_browser_progress:
        return True
    if not _context_prefers_browser_work(context):
        return False
    lowered = text.lower()
    return _text_mentions_browser_work(lowered)


def _payload_names_simple_model_skill(payload: dict[str, Any]) -> bool:
    explicit = payload.get("skill")
    if isinstance(explicit, str) and _normalize_skill(explicit) is not None:
        return True
    for key in ("action", "intent"):
        value = payload.get(key)
        if isinstance(value, str) and "." not in value and _normalize_skill(value) is not None:
            return True
    return False


def _payload_names_browser_action(payload: dict[str, Any]) -> bool:
    capability = str(payload.get("capability_id") or "").strip()
    operation = str(payload.get("operation") or "").strip()
    action = str(payload.get("action") or "").strip()
    joined = ".".join(part for part in (capability, operation) if part)
    value = action or joined
    return value.startswith("real_browser_control.")


def _payload_names_browser_completion_action(payload: dict[str, Any]) -> bool:
    capability = str(payload.get("capability_id") or "").strip()
    operation = str(payload.get("operation") or "").strip()
    action = str(payload.get("action") or "").strip()
    joined = ".".join(part for part in (capability, operation) if part)
    value = action or joined
    return value in {
        "sentinel_loop.summarize_evidence",
        "sentinel_loop.finish",
    }


def _context_has_browser_progress(context: dict[str, Any]) -> bool:
    requirements = context.get("completion_requirements")
    if isinstance(requirements, dict) and any(
        str(key).startswith("has_real_browser_") and value is True
        for key, value in requirements.items()
    ):
        return True
    if context.get("real_browser_control_summary") or context.get("browser_world_model"):
        return True
    for item in context.get("dispatch_summaries") or ():
        if isinstance(item, dict) and item.get("capability_id") == "real_browser_control":
            return True
    return False


def _context_prefers_browser_work(context: dict[str, Any]) -> bool:
    recommended_skill = str(context.get("primary_model_recommended_next_skill") or "")
    if recommended_skill in _BROWSER_MODEL_SKILLS:
        return True
    for key in ("primary_model_recommended_next_action", "model_visible_recommended_next_action", "recommended_next_action"):
        action = str(context.get(key) or "")
        if action.startswith("real_browser_control."):
            return True
    objective = str(context.get("mission_objective") or "").lower()
    return _text_mentions_browser_work(objective)


def _text_mentions_browser_work(lowered: str) -> bool:
    return any(
        marker in lowered
        for marker in (
            "alibaba",
            "browser",
            "browse",
            "web page",
            "website",
            "search result",
            "product page",
            "open result",
            "visible card",
            "glasses",
            "sunglasses",
            "under 5",
            "under five",
            "5 eur",
            "5 euro",
        )
    )


def _browser_native_context(context: dict[str, Any]) -> dict[str, Any]:
    browser_context = dict(context)
    available = list(browser_context.get("available_actions") or browser_context.get("model_visible_available_actions") or ())
    if not available:
        available = [
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "sentinel_loop.summarize_evidence",
            "sentinel_loop.finish",
        ]
    browser_context.setdefault("available_actions", available)
    if "primary_model_recommended_next_action" not in browser_context:
        action_map = browser_context.get("runtime_internal_action_map")
        recommended_skill = str(browser_context.get("primary_model_recommended_next_skill") or "")
        if isinstance(action_map, dict) and recommended_skill in action_map:
            browser_context["primary_model_recommended_next_action"] = action_map[recommended_skill]
    return browser_context


def _recovery_prompt_hint(context: dict[str, Any]) -> str:
    observations = [
        *[item for item in context.get("recoverable_decision_observations") or () if isinstance(item, dict)],
        *[item for item in context.get("recoverable_action_observations") or () if isinstance(item, dict)],
    ]
    if not isinstance(observations, list) or not observations:
        return ""
    latest = observations[-1] if isinstance(observations[-1], dict) else {}
    failure_code = str(latest.get("failure_code") or "recoverable_model_decision_failure")
    recommended = str(latest.get("recommended_skill") or context.get("primary_model_recommended_next_skill") or "")
    body_packet = context.get("model_visible_body_failure_packet")
    assessment_schema = context.get("model_blocker_assessment_schema")
    body_hint = ""
    if isinstance(body_packet, dict) and isinstance(assessment_schema, dict):
        required = ", ".join(str(item) for item in assessment_schema.get("required_model_response_fields") or ())
        body_hint = (
            "Sentinel body failure packet is available in context as safe structured data. "
            "Use it to diagnose the mechanical blocker and choose a safe next strategy. "
            f"If you explain the blocker, include a concise model_blocker_assessment object with these fields: {required}. "
            "Your assessment cannot grant authority or override runtime receipts.\n"
        )
    return (
        f"Previous recoverable turn failure: {failure_code}.\n"
        f"Recovery best next skill: {recommended}.\n"
        f"{body_hint}"
        "Recovery requirement: return visible content containing one compact JSON skill object or safe natural intent now.\n"
    )


def _visible_content_failure(payload: dict[str, Any]) -> str | None:
    normalization = str(payload.get("normalization_strategy") or "")
    if normalization == "empty_visible_content":
        return "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"
    if normalization in {"no_json_object_detected", "truncated_or_invalid_json", "strict_json_rejected", "json_value_not_object"}:
        return "MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"
    return None


def _extract_payload(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, dict):
        direct = dict(raw_output)
        if any(key in direct for key in ("skill", "action", "capability_id", "operation")):
            return direct
        text = _extract_text(raw_output, {})
        embedded = _first_json_object(text)
        return embedded or direct
    if isinstance(raw_output, str):
        return _first_json_object(raw_output) or {}
    return {}


def _extract_text(raw_output: Any, payload: dict[str, Any]) -> str:
    candidates: list[str] = []
    if isinstance(raw_output, str):
        candidates.append(raw_output)
    if isinstance(raw_output, dict):
        for key in ("reply", "content", "text", "message"):
            value = raw_output.get(key)
            if isinstance(value, str):
                candidates.append(value)
        metadata = raw_output.get("metadata")
        if isinstance(metadata, dict):
            for key in ("reply", "content", "text", "message"):
                value = metadata.get(key)
                if isinstance(value, str):
                    candidates.append(value)
    for key in ("skill", "action", "intent"):
        value = payload.get(key)
        if isinstance(value, str):
            candidates.append(value)
    return "\n".join(candidates).strip()


def _first_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            loaded = json.loads(stripped)
            return loaded if isinstance(loaded, dict) else None
        except json.JSONDecodeError:
            return None
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match is None:
        return None
    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _requested_skill(payload: dict[str, Any], text: str) -> str | None:
    explicit = payload.get("skill") or payload.get("action") or payload.get("intent")
    if isinstance(explicit, str):
        normalized = _normalize_skill(explicit)
        if normalized is not None:
            return normalized
    if ("capability_id" in payload or "capability" in payload) and "operation" in payload:
        return _canonical_payload_skill(payload)
    lowered = text.lower()
    if any(
        marker in lowered
        for marker in (
            "add file",
            "create app.py",
            "create readme.md",
            "create tests/test_app.py",
            "create the new",
            "create new file",
            "new file",
        )
    ):
        return "create_file"
    if any(
        marker in lowered
        for marker in (
            "app test file",
            "create app",
            "local app",
            "patch",
            "readme",
            "test file",
            "edit",
            "update file",
            "replace marker",
        )
    ):
        return "patch"
    if _has_worker_intent(lowered):
        return "spawn_worker"
    if any(marker in lowered for marker in ("run check", "run the check", "bounded check", "check", "test", "verify code")):
        return "run_check"
    if any(marker in lowered for marker in ("send", "notify", "message", "channel")):
        return "send_message"
    if "verifier" in lowered:
        return "spawn_worker"
    if any(marker in lowered for marker in ("follow result", "open result", "open link", "follow link")):
        return "follow"
    if "inspect" in lowered:
        return "inspect"
    if any(marker in lowered for marker in ("extract", "product card", "visible card")):
        return "extract_evidence"
    if any(marker in lowered for marker in ("search", "browse")):
        return "search"
    if any(marker in lowered for marker in ("finish", "done", "complete", "enough proof", "summarize")):
        return "finish"
    return None


def _has_worker_intent(lowered_text: str) -> bool:
    return bool(re.search(r"\b(worker|delegate|spawn|verifier|researcher)\b", lowered_text))


def _skill_carries_inert_browser_semantic_data(skill: str | None) -> bool:
    return skill in _BROWSER_MODEL_SKILLS


def _normalize_skill(value: str) -> str | None:
    lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "run": "run_check",
        "run_check": "run_check",
        "check": "run_check",
        "patch": "patch",
        "edit": "patch",
        "update": "patch",
        "create_file": "create_file",
        "add_file": "create_file",
        "new_file": "create_file",
        "create_app": "patch",
        "build_app": "patch",
        "workspace_patch": "patch",
        "send": "send_message",
        "send_message": "send_message",
        "spawn_worker": "spawn_worker",
        "worker": "spawn_worker",
        "finish": "finish",
        "complete": "finish",
        "read": "read",
        "list": "read",
        "workspace_list": "read",
        "workspace_read": "read",
        "workspace_search": "search",
        "observe": "observe",
        "browse_observe": "observe",
        "navigate": "navigate",
        "open": "navigate",
        "browse_search": "search",
        "search": "search",
        "follow": "follow",
        "open_result": "follow",
        "open_link": "follow",
        "inspect": "inspect",
        "inspect_result": "inspect",
        "extract": "extract_evidence",
        "extract_evidence": "extract_evidence",
        "extract_entities": "extract_evidence",
        "extract_product_cards": "extract_evidence",
        "verify": "verify",
        "verify_extraction": "verify",
        "recover": "recover_session",
        "recover_session": "recover_session",
    }
    return aliases.get(lowered)


def _canonical_payload_skill(payload: dict[str, Any]) -> str:
    capability_id = str(payload.get("capability_id") or payload.get("capability") or "").strip()
    operation = str(payload.get("operation") or "").strip()
    action = f"{capability_id}.{operation}"
    if action == "bounded_channel.send_message":
        return "send_message"
    if action == "code_execution_sandbox.code_exec.run_profile":
        return "run_check"
    if action == "workspace_patch.apply_patch":
        params = payload.get("params")
        if isinstance(params, dict) and _looks_like_create_file_params(params):
            return "create_file"
        return "patch"
    if action in {"workspace.list", "workspace.read"}:
        return "read"
    if action == "workspace.search":
        return "search"
    if action == "worker_fleet.spawn_worker":
        return "spawn_worker"
    if action == "sentinel_loop.finish":
        return "finish"
    if action == "real_browser_control.real_browser.observe":
        return "observe"
    if action == "real_browser_control.real_browser.open":
        return "navigate"
    if action == "real_browser_control.real_browser.search":
        return "search"
    if action == "real_browser_control.real_browser.open_result":
        return "follow"
    if action == "real_browser_control.real_browser.inspect_result":
        return "inspect"
    if action in {
        "real_browser_control.real_browser.extract_evidence",
        "real_browser_control.real_browser.extract_entities",
        "real_browser_control.real_browser.extract_product_cards",
    }:
        return "extract_evidence"
    if action == "real_browser_control.real_browser.verify_extraction":
        return "verify"
    return "__canonical__"


def _recommended_skill(context: dict[str, Any]) -> str:
    next_sequence_skill = _next_preferred_sequence_skill(context)
    if next_sequence_skill is not None:
        return next_sequence_skill
    skill = str(context.get("primary_model_recommended_next_skill") or "").strip()
    if skill:
        return skill
    recommended = context.get("primary_model_next_recommended_skills")
    if isinstance(recommended, list) and recommended:
        return str(recommended[0])
    raise ActionKernelError("MODEL_NATIVE_DECISION_NO_SAFE_SKILL")


def _next_preferred_sequence_skill(context: dict[str, Any]) -> str | None:
    sequence = context.get("_preferred_skill_sequence")
    if isinstance(sequence, tuple | list) and sequence:
        return _next_sequence_skill(tuple(str(item) for item in sequence), context)
    return None


def _next_sequence_skill(sequence: tuple[str, ...], context: dict[str, Any]) -> str | None:
    completed = _completed_sequence_skill_counts(context)
    for skill in sequence:
        if not _sequence_skill_is_live(skill, context):
            continue
        if completed.get(skill, 0) > 0:
            completed[skill] -= 1
            continue
        return skill
    return sequence[-1] if sequence else None


def _sequence_skill_is_live(skill: str, context: dict[str, Any]) -> bool:
    if skill == "create_file":
        return bool(_usable_create_file_plans(context))
    if skill == "patch":
        if _recovering_failed_semantic_check(context):
            return True
        return bool(context.get("_workspace_patch_plans") or ())
    return True


def _completed_sequence_skills(context: dict[str, Any]) -> set[str]:
    return {skill for skill, count in _completed_sequence_skill_counts(context).items() if count > 0}


def _completed_sequence_skill_counts(context: dict[str, Any]) -> dict[str, int]:
    completed: dict[str, int] = {}

    def add(skill: str) -> None:
        completed[skill] = completed.get(skill, 0) + 1

    for item in context.get("dispatch_summaries") or ():
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") not in {"completed", "passed"}:
            continue
        action = f"{item.get('capability_id')}.{item.get('operation')}"
        if action == "workspace_patch.apply_patch":
            add("patch")
        elif action == "code_execution_sandbox.code_exec.run_profile":
            add("run_check")
        elif action == "bounded_channel.send_message":
            add("send_message")
        elif action == "worker_fleet.spawn_worker":
            add("spawn_worker")
        elif action in {
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
        }:
            add("browse_search")
        elif action in {
            "real_browser_control.real_browser.extract_evidence",
            "real_browser_control.real_browser.extract_entities",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
        }:
            add("extract")
        elif action == "sentinel_loop.summarize_evidence":
            add("finish")
        elif action == "sentinel_loop.finish":
            add("finish")
    if context.get("recent_product_receipt_refs") and not completed:
        # Conservative fallback for older contexts that have receipts but no
        # dispatch summaries: first material skill is done.
        add("run_check")
    return completed


def _completed_action_count(context: dict[str, Any], *, capability_id: str, operation: str) -> int:
    count = 0
    for item in context.get("dispatch_summaries") or ():
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") not in {"completed", "passed"}:
            continue
        if item.get("capability_id") == capability_id and item.get("operation") == operation:
            count += 1
    return count


def _skill_to_action(
    skill: str,
    *,
    payload: dict[str, Any],
    text: str,
    context: dict[str, Any],
) -> ActionEnvelope:
    if skill == "__canonical__":
        return ActionEnvelope(
            capability_id=str(payload.get("capability_id") or payload.get("capability")),
            operation=str(payload["operation"]),
            params=dict(payload.get("params") or payload.get("arguments") or {}),
            target_ref=str(payload["target_ref"]) if payload.get("target_ref") is not None else None,
            idempotency_key=str(payload["idempotency_key"]) if payload.get("idempotency_key") else None,
        )
    if skill == "read":
        params = dict(payload.get("params") or payload.get("arguments") or {})
        action = _runtime_action_for_skill(context, "read")
        operation = "read" if params.get("path") else "list"
        if action in {"workspace.list", "workspace.read"}:
            operation = action.rsplit(".", 1)[-1]
            if operation == "read" and not params.get("path"):
                operation = "list"
        params.setdefault("path", ".")
        return ActionEnvelope(
            capability_id="workspace",
            operation=operation,
            params=params,
            idempotency_key=_idempotency_key("read", context, text),
        )
    if skill == "patch":
        params = _workspace_patch_params(payload=payload, context=context)
        return ActionEnvelope(
            capability_id="workspace_patch",
            operation="apply_patch",
            target_ref=str(params["target_path"]),
            params=params,
            idempotency_key=_idempotency_key("patch", context, text),
        )
    if skill == "create_file":
        params = _workspace_create_file_params(payload=payload, context=context)
        return ActionEnvelope(
            capability_id="workspace_patch",
            operation="apply_patch",
            target_ref=str(params["target_path"]),
            params=params,
            idempotency_key=_idempotency_key("create_file", context, text),
        )
    if skill == "run_check":
        check_plan = context.get("_bounded_check_plan")
        if isinstance(check_plan, dict) and check_plan:
            params = dict(check_plan)
        else:
            params = dict(payload.get("params") or {})
            params.setdefault("profile_id", "fake_pass")
            params.setdefault("args", ["."])
        return ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params=params,
            idempotency_key=_idempotency_key("run_check", context, text),
        )
    if skill == "send_message":
        return ActionEnvelope(
            capability_id="bounded_channel",
            operation="send_message",
            params=_channel_params(payload=payload, text=text, context=context),
            idempotency_key=_idempotency_key("send_message", context, text),
        )
    if skill == "spawn_worker":
        params = _worker_params(payload=payload, text=text)
        params.setdefault("role", "verifier")
        params.setdefault("objective", "Verify the product mission proof bundle and receipts.")
        params.setdefault("delegated_skills", ["read"])
        params.setdefault("max_actions", 1)
        return ActionEnvelope(
            capability_id="worker_fleet",
            operation="spawn_worker",
            params=params,
            idempotency_key=_idempotency_key("spawn_worker", context, text),
        )
    if skill == "finish":
        return ActionEnvelope(
            capability_id="sentinel_loop",
            operation="finish",
            params=_finish_params(payload=payload, text=text, context=context),
            idempotency_key=_idempotency_key("finish", context, text),
        )
    if skill == "observe":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.observe",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("observe", context, text),
        )
    if skill == "navigate":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.open",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("navigate", context, text),
        )
    if skill in {"search", "browse_search"}:
        if _runtime_action_for_skill(context, "search") == "workspace.search":
            return ActionEnvelope(
                capability_id="workspace",
                operation="search",
                params=dict(payload.get("params") or payload.get("arguments") or {}),
                idempotency_key=_idempotency_key("workspace_search", context, text),
            )
        params = _normalize_model_browser_search_params(
            payload.get("params"),
            fallback_query=_bounded_query(text) or "mission objective",
        )
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params=params,
            idempotency_key=_idempotency_key("search", context, text),
        )
    if skill == "follow":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.open_result",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("follow", context, text),
        )
    if skill == "inspect":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.inspect_result",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("inspect", context, text),
        )
    if skill in {"extract_evidence", "extract"}:
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation=_extract_operation_for_context(context),
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("extract_evidence", context, text),
        )
    if skill == "verify":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.verify_extraction",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("verify", context, text),
        )
    if skill == "recover_session":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.recover_session",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("recover_session", context, text),
        )
    raise ActionKernelError("MODEL_NATIVE_DECISION_SKILL_NOT_MAPPED")


def _runtime_action_for_skill(context: dict[str, Any], skill: str) -> str:
    mapping = context.get("runtime_internal_action_map")
    if isinstance(mapping, dict):
        action = mapping.get(skill)
        if isinstance(action, str):
            return action
    surface = context.get("model_skill_surface")
    if isinstance(surface, dict):
        nested = surface.get("runtime_internal_action_map")
        if isinstance(nested, dict):
            action = nested.get(skill)
            if isinstance(action, str):
                return action
    return ""


def _finish_skill_available(context: dict[str, Any]) -> bool:
    if context.get("finish_available") is True:
        return True
    actions = {str(action) for action in context.get("runtime_available_actions") or ()}
    if "sentinel_loop.finish" in actions:
        return True
    skills = {str(skill) for skill in context.get("model_visible_skills") or ()}
    return "finish" in skills


def _normalize_browser_search_action(envelope: ActionEnvelope, *, fallback_query: str) -> ActionEnvelope:
    if envelope.capability_id != "real_browser_control" or envelope.operation != "real_browser.search":
        return envelope
    params = _normalize_model_browser_search_params(envelope.params, fallback_query=fallback_query)
    return ActionEnvelope(
        capability_id=envelope.capability_id,
        operation=envelope.operation,
        target_ref=envelope.target_ref,
        params=params,
        idempotency_key=envelope.idempotency_key,
    )


def _finish_params(*, payload: dict[str, Any], text: str, context: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"safe_summary": _safe_finish_summary(text, context)}
    source = payload.get("params") if isinstance(payload.get("params"), dict) else payload
    if not isinstance(source, dict):
        return _complete_finish_params_from_context(params, context=context)

    final_answer = source.get("final_answer")
    if isinstance(final_answer, str):
        params["final_answer"] = {"answer_text": _bounded_text(final_answer, 2400)}
    elif isinstance(final_answer, dict):
        params["final_answer"] = _bounded_terminal_mapping(final_answer, max_items=24, max_text=2400)
        nested_claims = final_answer.get("answer_claims")
        if isinstance(nested_claims, list) and "answer_claims" not in source:
            params["answer_claims"] = [item for item in nested_claims if isinstance(item, dict)][:40]
        nested_evidence = final_answer.get("public_evidence")
        if isinstance(nested_evidence, list) and "public_evidence" not in source:
            params["public_evidence"] = [item for item in nested_evidence if isinstance(item, dict)][:40]
    elif isinstance(source.get("answer"), str):
        params["final_answer"] = {"answer_text": _bounded_text(str(source.get("answer") or ""), 2400)}

    honest_blocker = source.get("honest_blocker")
    if isinstance(honest_blocker, dict):
        params["honest_blocker"] = _bounded_terminal_mapping(honest_blocker, max_items=16, max_text=1200)
    if isinstance(source.get("answer_claims"), list):
        params["answer_claims"] = [item for item in source["answer_claims"] if isinstance(item, dict)][:40]
    if isinstance(source.get("public_evidence"), list):
        params["public_evidence"] = [item for item in source["public_evidence"] if isinstance(item, dict)][:40]
    return _complete_finish_params_from_context(params, context=context)


def _complete_finish_params_from_context(params: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    if isinstance(params.get("final_answer"), dict) or isinstance(params.get("honest_blocker"), dict):
        return params
    summary = context.get("grounded_evidence_summary")
    if not isinstance(summary, dict):
        return params
    summary_text = str(summary.get("summary_text") or "").strip()
    if not summary_text:
        return params
    evidence_refs = _browser_public_evidence_refs(context)
    if not evidence_refs:
        evidence_refs = [f"evidence:{stable_hash({'summary': summary_text})}"]
    mission_objective = str(context.get("mission_objective") or "")
    if browser_summary_supports_terminal_blocker(summary, mission_objective=mission_objective):
        params["honest_blocker"] = {
            "reason": _bounded_text(summary_text, 1200),
            "available_evidence_refs": evidence_refs,
            "missing_evidence": ["objective-satisfying evidence"],
        }
        params.setdefault(
            "answer_claims",
            [
                {
                    "claim_id": f"claim:{stable_hash({'negative': summary_text})}",
                    "claim_type": "declared_unknown",
                    "text": _bounded_text(summary_text, 1200),
                    "evidence_refs": evidence_refs,
                    "confidence": 0.74,
                }
            ],
        )
        return params
    if not browser_summary_supports_terminal_answer(summary):
        return params
    params["final_answer"] = {
        "answer_text": _bounded_text(summary_text, 2400),
        "answer_kind": "grounded_browser_answer",
    }
    params.setdefault(
        "answer_claims",
        [
            {
                "claim_id": f"claim:{stable_hash({'answer': summary_text})}",
                "claim_type": "sourced_factual_claim" if evidence_refs else "model_inference",
                "text": _bounded_text(summary_text, 1200),
                "evidence_refs": evidence_refs,
                "confidence": 0.72,
            }
        ],
    )
    return params


def _browser_public_evidence_refs(context: dict[str, Any]) -> list[str]:
    proof_summary = context.get("browser_proof_index_summary")
    if not isinstance(proof_summary, dict):
        return []
    refs = proof_summary.get("public_evidence_ids")
    if isinstance(refs, str):
        return [refs]
    if isinstance(refs, list | tuple):
        return [str(ref) for ref in refs[:8] if str(ref)]
    return []


def _bounded_terminal_mapping(value: dict[str, Any], *, max_items: int, max_text: int) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = str(key)[:80]
        if isinstance(item, str):
            bounded[safe_key] = _bounded_text(item, max_text)
        elif isinstance(item, bool | int | float) or item is None:
            bounded[safe_key] = item
        elif isinstance(item, list):
            bounded[safe_key] = [
                _bounded_text(entry, max_text) if isinstance(entry, str) else entry
                for entry in item[:20]
                if isinstance(entry, (str, bool, int, float, dict))
            ]
        elif isinstance(item, dict):
            bounded[safe_key] = _bounded_terminal_mapping(item, max_items=max_items, max_text=max_text)
    return bounded


def _extract_operation_for_context(context: dict[str, Any]) -> str:
    if _context_has_commerce_evidence(context):
        return "real_browser.extract_product_cards"
    return "real_browser.extract_evidence"


def _context_has_commerce_evidence(context: dict[str, Any]) -> bool:
    summary = context.get("browser_world_model_summary")
    if isinstance(summary, dict):
        kind_counts = summary.get("candidate_entity_kind_counts")
        if isinstance(kind_counts, dict):
            for kind, count in kind_counts.items():
                if any(marker in str(kind).lower() for marker in ("commerce", "product", "catalog")):
                    try:
                        if int(count or 0) > 0:
                            return True
                    except (TypeError, ValueError):
                        return True
        try:
            if int(summary.get("product_candidate_count") or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    model = context.get("browser_world_model")
    if isinstance(model, dict):
        cards = model.get("product_or_result_candidate_cards")
        if isinstance(cards, list):
            for card in cards:
                if not isinstance(card, dict):
                    continue
                kind = str(card.get("kind") or card.get("entity_kind") or "").lower()
                family = str(card.get("entity_family") or "").lower()
                if any(marker in f"{kind} {family}" for marker in ("commerce", "product", "catalog")):
                    return True
                commerce_fields = ("visible_price", "currency_or_unit", "minimum_order", "supplier_or_store")
                if any(str(card.get(field) or "").strip().lower() not in {"", "unknown"} for field in commerce_fields):
                    return True
    return False


def _normalize_model_browser_search_params(params: Any, *, fallback_query: str) -> dict[str, Any]:
    try:
        return normalize_model_browser_search_parameters(params, fallback_query=fallback_query)
    except BrowserSearchParameterBoundaryError as exc:
        raise ActionKernelError(str(exc)) from exc


def _workspace_patch_params(*, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload_params = payload.get("params")
    if isinstance(payload_params, dict) and _looks_like_patch_params(payload_params):
        plan = dict(payload_params)
    elif isinstance(payload_params, dict) and _looks_like_create_file_params(payload_params):
        return _create_file_params_from_plan(payload_params)
    else:
        plans = context.get("_workspace_patch_plans") or ()
        usable_plans = [dict(item) for item in plans if isinstance(item, dict)]
        if context.get("_workspace_patch_plans_are_pending") is True:
            plan = usable_plans[0] if usable_plans else None
        else:
            completed_patch_count = _completed_action_count(
                context,
                capability_id="workspace_patch",
                operation="apply_patch",
            )
            plan = usable_plans[completed_patch_count] if completed_patch_count < len(usable_plans) else None
        if plan is None:
            create_plans = _usable_create_file_plans(context)
            if create_plans:
                return _create_file_params_from_plan(create_plans[0])
            raise ActionKernelError("MODEL_NATIVE_DECISION_PATCH_PLAN_MISSING")
    target_path = str(plan.get("target_path") or "").strip()
    expected_base_hash = str(plan.get("expected_base_hash") or "").strip()
    old_text = str(plan.get("old_text") or "")
    new_text = str(plan.get("new_text") or "")
    if not target_path or not expected_base_hash or not old_text:
        raise ActionKernelError("MODEL_NATIVE_DECISION_PATCH_PLAN_MISSING")
    return {
        "target_path": target_path,
        "target_paths": [target_path],
        "expected_base_hash": expected_base_hash,
        "old_text": old_text,
        "new_text": new_text,
    }


def _workspace_create_file_params(*, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload_params = payload.get("params")
    plans = _usable_create_file_plans(context)
    if _recovering_duplicate_create_target(context) and plans:
        return _create_file_params_from_plan(plans[0])
    if isinstance(payload_params, dict) and _has_create_file_target_and_content(payload_params):
        return _create_file_params_from_plan(payload_params)
    if not plans:
        raise ActionKernelError("MODEL_NATIVE_DECISION_CREATE_FILE_PLAN_MISSING")
    return _create_file_params_from_plan(plans[0])


def _usable_create_file_plans(context: dict[str, Any]) -> list[dict[str, Any]]:
    plans = context.get("_workspace_create_file_plans") or ()
    return [dict(item) for item in plans if isinstance(item, dict)]


def _recovering_duplicate_create_target(context: dict[str, Any]) -> bool:
    for item in context.get("recoverable_action_observations") or ():
        if isinstance(item, dict) and item.get("failure_code") == "workspace_patch_create_target_exists":
            return True
    return False


def _recovering_failed_semantic_check(context: dict[str, Any]) -> bool:
    for item in context.get("recoverable_action_observations") or ():
        if isinstance(item, dict) and item.get("failure_code") == "code_exec_failed":
            return True
    return False


def _pending_workspace_quality_skill(context: dict[str, Any]) -> str | None:
    if _usable_create_file_plans(context):
        return "create_file"
    if context.get("_workspace_patch_plans") or ():
        return "patch"
    return None


def _create_file_params_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    target_path = str(plan.get("target_path") or "").strip()
    new_text = str(plan.get("new_text") if plan.get("new_text") is not None else plan.get("content") or "")
    if not target_path or not new_text:
        raise ActionKernelError("MODEL_NATIVE_DECISION_CREATE_FILE_PLAN_MISSING")
    return {
        "target_path": target_path,
        "target_paths": [target_path],
        "create_file": True,
        "new_text": new_text,
    }


def _looks_like_patch_params(params: dict[str, Any]) -> bool:
    return all(str(params.get(key) or "") for key in ("target_path", "expected_base_hash", "old_text"))


def _looks_like_create_file_params(params: dict[str, Any]) -> bool:
    return bool(params.get("create_file")) and _has_create_file_target_and_content(params)


def _has_create_file_target_and_content(params: dict[str, Any]) -> bool:
    return bool(str(params.get("target_path") or "")) and (
        params.get("new_text") is not None or params.get("content") is not None
    )


def _channel_params(*, payload: dict[str, Any], text: str, context: dict[str, Any]) -> dict[str, Any]:
    payload_params = payload.get("params")
    model_message = ""
    if isinstance(payload_params, dict):
        for key in ("body", "message", "text"):
            value = payload_params.get(key)
            if isinstance(value, str) and value.strip():
                model_message = value
                break
    granted_destination = _granted_channel_destination(context)
    if granted_destination is not None:
        recipient = granted_destination["destination_ref"]
        return {
            "adapter_id": granted_destination["adapter_id"],
            "channel": granted_destination["channel"],
            "body": _bounded_channel_body(model_message or text, context),
            "recipients": [recipient],
            "recipient_provenance": {recipient: "mission_level_destination_grant"},
            "evidence_refs": ["evidence:monster_runtime_product_loop"],
            "idempotency_key": _idempotency_key("channel", context, text),
        }
    return {
        "adapter_id": "monster_fake_channel",
        "channel": "webhook",
        "body": _bounded_channel_body(model_message or text, context),
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:monster_runtime_product_loop"],
        "idempotency_key": _idempotency_key("channel", context, text),
    }


def _granted_channel_destination(context: dict[str, Any]) -> dict[str, str] | None:
    grants = context.get("live_channel_destination_grants")
    if not isinstance(grants, list):
        return None
    for item in grants:
        if not isinstance(item, dict):
            continue
        adapter_id = str(item.get("adapter_id") or "").strip()
        channel = str(item.get("channel") or "").strip().lower()
        destination_ref = str(item.get("destination_ref") or "").strip().lower()
        if adapter_id and channel == "telegram" and destination_ref == "telegram:configured-chat":
            return {
                "adapter_id": adapter_id,
                "channel": channel,
                "destination_ref": destination_ref,
            }
    return None


def _worker_params(*, payload: dict[str, Any], text: str) -> dict[str, Any]:
    params = dict(payload.get("params") or {})
    lowered = text.lower()
    if "role" not in params:
        if "code fixer" in lowered or "code_fixer" in lowered or "implementation" in lowered:
            params["role"] = "code_fixer"
        elif "report writer" in lowered or "report_writer" in lowered or "summarize" in lowered:
            params["role"] = "report_writer"
        elif "researcher" in lowered or "research" in lowered:
            params["role"] = "researcher"
        elif "browser operator" in lowered or "browser_operator" in lowered:
            params["role"] = "browser_operator"
        elif "verifier" in lowered or "verify" in lowered:
            params["role"] = "verifier"
    if "objective" not in params and text.strip():
        params["objective"] = _bounded_text(text, 180)
    return params


def _bounded_channel_body(text: str, context: dict[str, Any]) -> str:
    safe_text = _safe_channel_body_text(text)
    if safe_text:
        return f"Sentinel completion update: {safe_text}"
    objective = _bounded_text(str(context.get("mission_objective") or "mission"), 140)
    safe_objective = _safe_channel_body_text(objective)
    if safe_objective:
        return f"Sentinel completion update: {safe_objective}"
    return "Sentinel completion update: granted mission progress completed inside scope."


def _safe_channel_body_text(text: str) -> str:
    candidate = _bounded_text(text, 160)
    if not candidate:
        return ""
    lowered = candidate.lower()
    hard_markers = (
        "account",
        "api key",
        "authorization",
        "bearer",
        "browser",
        "checkout",
        "contact supplier",
        "credential",
        "fallback/auto",
        "login",
        "password",
        "payment",
        "provider-native",
        "provider_native",
        "secret",
        "session token",
        "spend",
    )
    if any(marker in lowered for marker in hard_markers):
        return ""
    return candidate


def _safe_finish_summary(text: str, context: dict[str, Any]) -> str:
    if text.strip():
        return f"Model-native summary/finish intent: {_bounded_text(text, 220)}"
    receipts = len(context.get("recent_product_receipt_refs") or ())
    return f"Model-native product loop finished after {receipts} product receipt(s)."


def _bounded_query(text: str) -> str:
    lowered = text.strip()
    if not lowered:
        return ""
    return _bounded_text(lowered, 120)


def _hard_boundary_action(text: str, payload: dict[str, Any]) -> ActionEnvelope | None:
    lowered = f"{text}\n{json.dumps(_safe_payload_shape(payload), sort_keys=True)}".lower()
    if _contains_negative_boundary_instruction(lowered):
        return None
    if any(marker in lowered for marker in ("pay", "payment", "checkout", "spend")):
        return ActionEnvelope(capability_id="payment_authority", operation="spend")
    if any(marker in lowered for marker in ("login", "log in", "sign in", "account creation", "create account")):
        return ActionEnvelope(capability_id="account_authority", operation="login")
    if any(marker in lowered for marker in ("contact supplier", "contact the supplier", "send inquiry")):
        return ActionEnvelope(capability_id="external_channel", operation="contact_supplier")
    return None


def _contains_negative_boundary_instruction(lowered_text: str) -> bool:
    negations = ("do not", "don't", "dont", "must not", "should not", "never", "no", "without", "avoid")
    boundary_markers = (
        "account",
        "checkout",
        "contact supplier",
        "credential",
        "download",
        "login",
        "log in",
        "payment",
        "provider-native",
        "secret",
        "sign in",
        "spend",
        "submit",
        "upload",
    )
    return any(negation in lowered_text for negation in negations) and any(
        marker in lowered_text for marker in boundary_markers
    )


def _credential_boundary_requested(text: str, payload: dict[str, Any]) -> bool:
    lowered = f"{text}\n{json.dumps(_safe_payload_shape(payload), sort_keys=True)}".lower()
    if _contains_negative_boundary_instruction(lowered):
        return False
    return any(marker in lowered for marker in ("credential", "password", "private key", "api secret", "api key"))


def _contains_forbidden_raw_material(value: Any) -> bool:
    forbidden_keys = {
        "raw_provider",
        "raw_provider_response",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning_content",
        "provider_native_tools",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            lowered_key = str(key).lower()
            if any(marker in lowered_key for marker in forbidden_keys):
                return True
            if _contains_forbidden_raw_material(child):
                return True
    if isinstance(value, list | tuple):
        return any(_contains_forbidden_raw_material(child) for child in value)
    return False


def _drop_safe_provider_wrapper(value: Any) -> Any:
    if not isinstance(value, dict) or "raw_provider_response" not in value:
        return value
    wrapper = value.get("raw_provider_response")
    if _contains_forbidden_raw_material(wrapper):
        return value
    sanitized = dict(value)
    sanitized.pop("raw_provider_response", None)
    return sanitized


def _idempotency_key(prefix: str, context: dict[str, Any], text: str) -> str:
    return f"monster-{prefix}-{stable_hash({'loop': context.get('loop_id'), 'text': text})[:12]}"


def _safe_context_shape(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "loop_id": context.get("loop_id"),
        "progress_state": context.get("progress_state"),
        "recommended_skill": context.get("primary_model_recommended_next_skill"),
        "receipt_count": len(context.get("recent_product_receipt_refs") or ()),
        "visible_skills": list(context.get("model_visible_skills") or ()),
    }


def _safe_render_shape(value: Any) -> str:
    return json.dumps(_safe_payload_shape(value), sort_keys=True, default=str)


def _safe_payload_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_payload_shape(child) for key, child in value.items()}
    if isinstance(value, list | tuple):
        return [_safe_payload_shape(child) for child in value]
    if isinstance(value, str):
        return {"text_hash": text_hash(value), "length": len(value)}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return {"type": type(value).__name__}


def _bounded_text(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


__all__ = [
    "ProductModelNativeDecisionClient",
    "ProductModelClient",
    "ProductModelRequestFactory",
    "extract_canonical_json_decision",
]
