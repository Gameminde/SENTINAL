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
        response = provider.execute(request, timeout=provider.default_timeout_policy(), credential=credential)
        if response is None:
            return _blocked("MODEL_EXECUTION_DEFERRED")
        if response.error_class:
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


def _blocked(reason: str, *, provider_response_hash: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"blocked_reason": reason}
    if provider_response_hash is not None:
        metadata["provider_response_hash"] = provider_response_hash
    return {
        "reply": f"LLM operator model call blocked: {reason}.",
        "metadata": metadata,
    }
