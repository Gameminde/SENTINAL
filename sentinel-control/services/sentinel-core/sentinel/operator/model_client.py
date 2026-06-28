from __future__ import annotations

import os
import ipaddress
from typing import Any
from urllib.parse import urlparse

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.catalog import ProviderCatalog, ProviderFamily
from sentinel.agent.model_execution.credentials import ProviderCredentialHandle, ProviderCredentialSource
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog
from sentinel.agent.model_execution.redaction import stable_hash, text_hash


class OperatorCatalogModelClient:
    """Explicit UserModelContract -> catalog provider client for cockpit LLM mode.

    This client does not select a provider, backend, or model. It only executes
    the already user-selected contract when the catalog has a compatible
    backend. Unsupported/missing cases fail closed as structured operator data.
    """

    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        provider_catalog: ProviderCatalog | None = None,
    ) -> None:
        self._contract = user_model_contract
        self._catalog = provider_catalog or build_default_provider_catalog()

    def complete(self, request: RealModelRequest) -> dict[str, Any]:
        mismatch_reason = self._contract_mismatch(request)
        if mismatch_reason is not None:
            return _blocked(mismatch_reason)
        try:
            entry = self._catalog.get(request.provider_id)
        except LookupError:
            return _blocked("UNKNOWN_PROVIDER")
        backend = next((candidate for candidate in entry.backends if candidate.backend_id == request.backend_id), None)
        if backend is None or not backend.supports_model(request.model_id):
            return _blocked("DISABLED_BACKEND")
        if _is_local_backend(entry, backend) and not _is_loopback_endpoint(backend.endpoint_template):
            return _blocked("LOCAL_ENDPOINT_NOT_LOOPBACK")
        if backend.family not in {
            ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
            ProviderFamily.DEEPSEEK_COMPATIBLE,
            ProviderFamily.MISTRAL_NATIVE_OR_COMPATIBLE,
            ProviderFamily.XAI_COMPATIBLE_OR_NATIVE,
        }:
            return _blocked("UNSUPPORTED_BACKEND_FAMILY")

        provider = OpenAICompatibleChatProvider(
            config=OpenAICompatibleProviderConfig(
                provider_id=entry.provider_id,
                backend_id=backend.backend_id,
                base_url=_base_url_from_endpoint(backend.endpoint_template),
                credential_env=entry.credential_policy.credential_env_var,
                default_model_id=request.model_id,
                backend_profile=backend,
            )
        )
        if request.runtime == "operator_llm_conversation" and backend.supports_json_mode:
            request_metadata = {
                **request.request_metadata,
                "response_format_json_object": True,
            }
            request = request.model_copy(
                update={
                    "request_metadata": request_metadata,
                    "request_hash": stable_hash(
                        {
                            "previous_request_hash": request.request_hash,
                            "request_metadata": request_metadata,
                        }
                    ),
                }
            )
        credential = _credential(entry.provider_id, entry.credential_policy.credential_env_var)
        try:
            timeout_policy = _provider_timeout_policy(provider=provider, request=request)
        except ValueError:
            return _blocked("READ_ONLY_TIMEOUT_POLICY_INVALID")
        response = provider.execute(request, timeout=timeout_policy, credential=credential)
        if response is None:
            return _blocked("MODEL_EXECUTION_DEFERRED")
        if response.error_class:
            if response.content:
                return _provider_failure_payload(
                    entry=entry,
                    backend=backend,
                    request=request,
                    response=response,
                )
            return _blocked(response.error_class, provider_response_hash=response.sanitized_response_hash)
        content = dict(response.content)
        content.setdefault("raw_provider_response", response.content)
        return content

    def _contract_mismatch(self, request: RealModelRequest) -> str | None:
        if request.provider_id != self._contract.selected_provider_id:
            return "PROVIDER_CONTRACT_MISMATCH"
        if request.backend_id != self._contract.selected_backend_id:
            return "BACKEND_CONTRACT_MISMATCH"
        if request.model_id != self._contract.selected_model:
            return "MODEL_CONTRACT_MISMATCH"
        return None


def _credential(provider_id: str, credential_env: str | None) -> ProviderCredentialHandle:
    if credential_env:
        return ProviderCredentialHandle.from_env(provider_id=provider_id, env_var_name=credential_env, scopes=["model:read"])
    return ProviderCredentialHandle(
        source_type=ProviderCredentialSource.ENV,
        provider_id=provider_id,
        source_ref_hash=text_hash(""),
        scopes=["model:read"],
    )


def _base_url_from_endpoint(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    suffix = "/chat/completions"
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)]
    return normalized


def _is_local_backend(entry: Any, backend: Any) -> bool:
    return (
        backend.family is ProviderFamily.LOCAL_OPENAI_COMPATIBLE
        or bool(getattr(entry.capability_flags, "local_runtime", False))
        or entry.credential_policy.credential_source_type == "local_none"
    )


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
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _provider_timeout_policy(*, provider: OpenAICompatibleChatProvider, request: RealModelRequest) -> ModelTimeoutPolicy:
    if request.request_metadata.get("read_only_lane") != "exploration_decision":
        return provider.default_timeout_policy()
    timeout_payload = request.request_metadata.get("timeout_policy")
    if not isinstance(timeout_payload, dict):
        return provider.default_timeout_policy()
    try:
        return ModelTimeoutPolicy.model_validate(timeout_payload)
    except ValueError:
        raise ValueError("invalid read-only timeout policy") from None


def _provider_failure_payload(
    *,
    entry: Any,
    backend: Any,
    request: RealModelRequest,
    response: Any,
) -> dict[str, Any]:
    diagnostic = response.content if isinstance(response.content, dict) else {}
    payload: dict[str, Any] = {
        "provider_failure": True,
        "provider_failure_category": _provider_failure_category(response.error_class, diagnostic),
        "provider_error_class": str(response.error_class or "PROVIDER_ERROR"),
        "provider_id": entry.provider_id,
        "backend_id": backend.backend_id,
        "model_id": request.model_id,
        "endpoint_hash": text_hash(str(getattr(backend, "endpoint_template", ""))),
        "provider_response_hash": response.sanitized_response_hash,
        "diagnostic_retention_status": "retained",
        "data_not_authority": True,
        "can_execute": False,
    }
    for key in (
        "http_status",
        "provider_error_code",
        "provider_error_type",
        "provider_error_code_hash",
        "provider_error_type_hash",
        "provider_error_message_hash",
        "provider_error_message_redacted",
        "provider_error_body_hash",
        "rejected_reason",
        "content_extraction_source",
        "content_extraction_error",
    ):
        value = diagnostic.get(key)
        if isinstance(value, (str, int, bool)) or value is None:
            if value is not None:
                payload[key] = value
    return payload


def _provider_failure_category(error_class: str | None, diagnostic: dict[str, Any]) -> str:
    if error_class == "RATE_LIMIT":
        return "PROVIDER_RATE_LIMIT"
    if error_class == "MISSING_CREDENTIAL":
        return "PROVIDER_AUTH_ERROR"
    status = diagnostic.get("http_status")
    if status in {401, 403}:
        return "PROVIDER_AUTH_ERROR"
    if status == 429:
        return "PROVIDER_RATE_LIMIT"
    if status == 400:
        return "PROVIDER_BAD_REQUEST"
    if isinstance(status, int) and 500 <= status:
        return "PROVIDER_MODEL_UNAVAILABLE"
    if error_class == "TIMEOUT":
        return "PROVIDER_TRANSPORT_ERROR"
    if error_class == "INVALID_RESPONSE_SCHEMA":
        return "PROVIDER_TRANSPORT_ERROR"
    return "PROVIDER_UNKNOWN_ERROR"


def build_safe_provider_inventory(*, provider_catalog: ProviderCatalog | None = None) -> dict[str, Any]:
    catalog = provider_catalog or build_default_provider_catalog()
    providers: dict[str, Any] = {}
    plain_chat_families = {
        ProviderFamily.OPENAI_COMPATIBLE_CHAT,
        ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
        ProviderFamily.DEEPSEEK_COMPATIBLE,
        ProviderFamily.MISTRAL_NATIVE_OR_COMPATIBLE,
        ProviderFamily.XAI_COMPATIBLE_OR_NATIVE,
    }
    for provider_id in catalog.provider_ids():
        entry = catalog.get(provider_id)
        backend_ids = [backend.backend_id for backend in entry.backends]
        model_ids: list[str] = []
        endpoint_hashes: dict[str, str] = {}
        for backend in entry.backends:
            model_ids.extend(backend.supported_models)
            endpoint_hashes[backend.backend_id] = text_hash(backend.endpoint_template)
        credential_env = entry.credential_policy.credential_env_var
        providers[provider_id] = {
            "provider_id": provider_id,
            "backend_ids": backend_ids,
            "model_ids": sorted(dict.fromkeys(model_ids)),
            "plain_chat_completion": entry.family in plain_chat_families,
            "provider_native_tools_disabled": not entry.capability_flags.server_side_tools_enabled_by_default,
            "process_scoped_credentials": entry.credential_policy.credential_source_type == "env",
            "credential_present": bool(credential_env and os.environ.get(credential_env)),
            "credential_env_var": credential_env,
            "endpoint_hashes": endpoint_hashes,
            "status": entry.status.value,
        }
    return {
        "schema_version": "provider_inventory_safe/v1",
        "data_not_authority": True,
        "can_execute": False,
        "fallback_auto_enabled": False,
        "providers": providers,
    }


def _blocked(reason: str, *, provider_response_hash: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"blocked_reason": reason}
    if provider_response_hash is not None:
        metadata["provider_response_hash"] = provider_response_hash
    return {
        "reply": f"LLM operator model call blocked: {reason}.",
        "metadata": metadata,
    }
