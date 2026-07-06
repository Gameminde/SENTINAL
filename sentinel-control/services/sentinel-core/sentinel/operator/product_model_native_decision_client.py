from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError


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
    ) -> None:
        self._model_client = model_client
        self._request_factory = request_factory
        self._preferred_skill_sequence = tuple(preferred_skill_sequence)
        self.call_count = 0
        self.safe_diagnostics: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        context = dict(context)
        if self._preferred_skill_sequence:
            context["_preferred_skill_sequence"] = self._preferred_skill_sequence
        prompt = _compile_model_native_prompt(context)
        request = self._request_factory(context, prompt)
        raw_output = self._model_client.complete(request)
        self.call_count += 1
        sanitized_output = _drop_safe_provider_wrapper(raw_output)
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
    return (
        "You are the brain. Sentinel is the body/runtime/proof layer.\n"
        f"Mission objective: {objective}\n"
        f"Progress: {progress}\n"
        f"Visible skills: {skills}\n"
        f"Best next skill: {recommended}\n"
        f"Product receipts so far: {receipt_count}\n"
        f"{recovery_hint}"
        f"{workspace_hint}"
        "Choose exactly one next skill for this turn.\n"
        "Prefer one compact JSON object such as "
        "{\"skill\":\"create_file\",\"params\":{\"target_path\":\"app.py\",\"new_text\":\"...\"}}, "
        "{\"skill\":\"patch\",\"params\":{\"target_path\":\"app.py\",\"expected_base_hash\":\"...\",\"old_text\":\"...\",\"new_text\":\"...\"}}, "
        "{\"skill\":\"patch\"}, {\"skill\":\"run_check\"}, "
        "{\"skill\":\"send_message\"}, {\"skill\":\"spawn_worker\"}, or {\"skill\":\"finish\"}.\n"
        "Natural intent is acceptable when the transport preserves visible text, but JSON is most reliable.\n"
        "Do not request login, payment, credentials, provider-native tools, or fallback/AUTO."
    )


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


def _map_output_to_action(raw_output: Any, *, context: dict[str, Any]) -> ActionEnvelope:
    if isinstance(raw_output, ActionEnvelope):
        return raw_output
    payload = _extract_payload(raw_output)
    text = _extract_text(raw_output, payload)
    visible_content_failure = _visible_content_failure(payload)
    if visible_content_failure is not None and not text.strip():
        raise ActionKernelError(visible_content_failure)
    hard_boundary = _hard_boundary_action(text, payload)
    if hard_boundary is not None:
        return hard_boundary
    if _credential_boundary_requested(text, payload):
        raise ActionKernelError("MODEL_NATIVE_DECISION_HARD_BOUNDARY_CREDENTIAL_ACCESS")
    skill = _requested_skill(payload, text)
    if skill is None:
        skill = _recommended_skill(context)
    return _skill_to_action(skill, payload=payload, text=text, context=context)


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
    return (
        f"Previous recoverable turn failure: {failure_code}.\n"
        f"Recovery best next skill: {recommended}.\n"
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
    if "capability_id" in payload and "operation" in payload:
        return "__canonical__"
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
    if any(marker in lowered for marker in ("extract", "product card", "visible card")):
        return "extract"
    if any(marker in lowered for marker in ("search", "browse", "inspect")):
        return "browse_search"
    if any(marker in lowered for marker in ("finish", "done", "complete", "enough proof", "summarize")):
        return "finish"
    return None


def _has_worker_intent(lowered_text: str) -> bool:
    return bool(re.search(r"\b(worker|delegate|spawn|verifier|researcher)\b", lowered_text))


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
        "browse_search": "browse_search",
        "search": "browse_search",
        "extract": "extract",
        "extract_product_cards": "extract",
    }
    return aliases.get(lowered)


def _recommended_skill(context: dict[str, Any]) -> str:
    sequence = context.get("_preferred_skill_sequence")
    if isinstance(sequence, tuple | list) and sequence:
        next_skill = _next_sequence_skill(tuple(str(item) for item in sequence), context)
        if next_skill is not None:
            return next_skill
    skill = str(context.get("primary_model_recommended_next_skill") or "").strip()
    if skill:
        return skill
    recommended = context.get("primary_model_next_recommended_skills")
    if isinstance(recommended, list) and recommended:
        return str(recommended[0])
    raise ActionKernelError("MODEL_NATIVE_DECISION_NO_SAFE_SKILL")


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
            capability_id=str(payload["capability_id"]),
            operation=str(payload["operation"]),
            params=dict(payload.get("params") or {}),
            target_ref=str(payload["target_ref"]) if payload.get("target_ref") is not None else None,
            idempotency_key=str(payload["idempotency_key"]) if payload.get("idempotency_key") else None,
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
            params={"safe_summary": _safe_finish_summary(text, context)},
            idempotency_key=_idempotency_key("finish", context, text),
        )
    if skill == "browse_search":
        params = dict(payload.get("params") or {})
        params.setdefault("query", _bounded_query(text) or "mission objective")
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params=params,
            idempotency_key=_idempotency_key("browse_search", context, text),
        )
    if skill == "extract":
        return ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.extract_product_cards",
            params=dict(payload.get("params") or {}),
            idempotency_key=_idempotency_key("extract", context, text),
        )
    raise ActionKernelError("MODEL_NATIVE_DECISION_SKILL_NOT_MAPPED")


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
    return {
        "adapter_id": "monster_fake_channel",
        "channel": "webhook",
        "body": _bounded_channel_body(model_message or text, context),
        "recipients": ["founder@example.com"],
        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
        "evidence_refs": ["evidence:monster_runtime_product_loop"],
        "idempotency_key": _idempotency_key("channel", context, text),
    }


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
    if text.strip():
        return f"Sentinel completion update: {_bounded_text(text, 160)}"
    objective = _bounded_text(str(context.get("mission_objective") or "mission"), 140)
    return f"Sentinel completion update: {objective}"


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
    if any(marker in lowered for marker in ("pay", "payment", "checkout", "spend")):
        return ActionEnvelope(capability_id="payment_authority", operation="spend")
    if any(marker in lowered for marker in ("login", "log in", "sign in", "account creation", "create account")):
        return ActionEnvelope(capability_id="account_authority", operation="login")
    if any(marker in lowered for marker in ("contact supplier", "contact the supplier", "send inquiry")):
        return ActionEnvelope(capability_id="external_channel", operation="contact_supplier")
    return None


def _credential_boundary_requested(text: str, payload: dict[str, Any]) -> bool:
    lowered = f"{text}\n{json.dumps(_safe_payload_shape(payload), sort_keys=True)}".lower()
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


__all__ = ["ProductModelNativeDecisionClient", "ProductModelClient", "ProductModelRequestFactory"]
