from __future__ import annotations

from enum import Enum
import re
from typing import Any, Iterable

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel


_SECRET_LIKE_PATTERNS = (
    "sk-or-v1",
    "gsk_",
    "nvapi-",
    "Authorization: Bearer",
    "credential_value",
    "api_key_value",
)
_SECRET_LIKE_REGEXES = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}"),
)


class ProviderFamily(str, Enum):
    OPENAI_COMPATIBLE_CHAT = "OPENAI_COMPATIBLE_CHAT"
    OPENAI_NATIVE = "OPENAI_NATIVE"
    ANTHROPIC_MESSAGES_NATIVE = "ANTHROPIC_MESSAGES_NATIVE"
    GEMINI_NATIVE = "GEMINI_NATIVE"
    XAI_COMPATIBLE_OR_NATIVE = "XAI_COMPATIBLE_OR_NATIVE"
    MISTRAL_NATIVE_OR_COMPATIBLE = "MISTRAL_NATIVE_OR_COMPATIBLE"
    DEEPSEEK_COMPATIBLE = "DEEPSEEK_COMPATIBLE"
    COHERE_NATIVE = "COHERE_NATIVE"
    LOCAL_OPENAI_COMPATIBLE = "LOCAL_OPENAI_COMPATIBLE"


class ProviderCatalogStatus(str, Enum):
    ACTIVE = "active"
    DIAGNOSTIC = "diagnostic"
    LOCAL_ONLY = "local_only"
    PLANNED = "planned"
    DISABLED = "disabled"


class ProviderRealTestStatusKind(str, Enum):
    NOT_STARTED = "not_started"
    SKIP_SAFE_ONLY = "skip_safe_only"
    SUCCESS_VALIDATED = "success_validated"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    BLOCKED = "blocked"


class ProviderUsageMapping(SentinelModel):
    input_tokens_path: str | None = None
    output_tokens_path: str | None = None
    total_tokens_path: str | None = None
    reasoning_tokens_path: str | None = None
    cache_hit_tokens_path: str | None = None
    cache_miss_tokens_path: str | None = None
    cost_fields_supported: bool = False


class ProviderTimeoutProfile(SentinelModel):
    connect_timeout_seconds: float = Field(default=2.0, gt=0.0)
    read_timeout_seconds: float = Field(default=10.0, gt=0.0)
    total_timeout_seconds: float = Field(default=12.0, gt=0.0)
    reasoning_timeout_multiplier: float = Field(default=1.0, ge=1.0)
    stream_idle_timeout_seconds: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def _validate_timeout_bounds(self) -> ProviderTimeoutProfile:
        if self.total_timeout_seconds < self.connect_timeout_seconds:
            raise ValueError("total timeout must be at least connect timeout.")
        if self.total_timeout_seconds < self.read_timeout_seconds:
            raise ValueError("total timeout must be at least read timeout.")
        return self


class ProviderRetryPolicy(SentinelModel):
    max_attempts: int = Field(default=1, ge=1, le=3)
    retryable_statuses: list[int] = Field(default_factory=list)
    retryable_outcomes: list[str] = Field(default_factory=list)
    backoff_strategy: str = "none"
    jitter: bool = False

    @model_validator(mode="after")
    def _validate_backoff_strategy(self) -> ProviderRetryPolicy:
        if self.backoff_strategy not in {"none", "fixed", "exponential"}:
            raise ValueError("unsupported backoff strategy.")
        return self


class ProviderReasoningRedactionPolicy(SentinelModel):
    raw_reasoning_fields: list[str] = Field(
        default_factory=lambda: [
            "reasoning",
            "reasoning_content",
            "reasoning_details",
            "thinking",
            "thought",
            "thought_signature",
            "thinking_blocks",
        ]
    )
    request_reasoning_disable_fields: dict[str, Any] = Field(default_factory=dict)
    durable_reasoning_fields_allowed: list[str] = Field(
        default_factory=lambda: [
            "reasoning_enabled",
            "reasoning_present",
            "reasoning_hash",
            "reasoning_token_count",
        ]
    )
    stores_raw_reasoning: bool = False
    metadata_only: bool = True

    @model_validator(mode="after")
    def _validate_no_raw_reasoning_storage(self) -> ProviderReasoningRedactionPolicy:
        if self.stores_raw_reasoning:
            raise ValueError("raw reasoning cannot be durable catalog metadata.")
        return self


class ProviderCapabilityFlags(SentinelModel):
    chat: bool = False
    responses: bool = False
    messages: bool = False
    generate_content: bool = False
    streaming: bool = False
    json_mode: bool = False
    json_schema: bool = False
    tool_calling: bool = False
    server_side_tools: bool = False
    reasoning_controls: bool = False
    local_runtime: bool = False
    vision: bool = False
    audio: bool = False
    grants_tool_execution: bool = False
    grants_organ_execution: bool = False
    server_side_tools_enabled_by_default: bool = False

    @model_validator(mode="after")
    def _validate_capabilities_are_descriptive(self) -> ProviderCapabilityFlags:
        if self.grants_tool_execution or self.grants_organ_execution:
            raise ValueError("provider capability flags cannot grant execution authority.")
        if self.server_side_tools_enabled_by_default:
            raise ValueError("server-side provider tools must be disabled by default.")
        return self


class ProviderCredentialPolicy(SentinelModel):
    credential_env_var: str | None = None
    credential_source_type: str = "env"
    required_for_real_call: bool = True
    secret_free_handle_required: bool = True
    allowed_scopes: list[str] = Field(default_factory=lambda: ["model:read"])
    missing_credential_outcome: str = "MISSING_CREDENTIAL"

    @model_validator(mode="after")
    def _validate_secret_free_policy(self) -> ProviderCredentialPolicy:
        if not self.secret_free_handle_required:
            raise ValueError("provider credentials must use secret-free handles.")
        if self.credential_env_var and _contains_secret_like_value(self.credential_env_var):
            raise ValueError("credential env var metadata contains secret-like value.")
        return self


class ProviderRecommendation(SentinelModel):
    recommended_for: list[str] = Field(default_factory=list)
    avoid_for: list[str] = Field(default_factory=list)
    latency_class: str = "unknown"
    cost_class: str = "unknown"
    reliability_class: str = "unknown"
    notes: list[str] = Field(default_factory=list)
    fallback_provider_ids: list[str] = Field(default_factory=list)
    metadata_only: bool = True
    can_execute: bool = False
    fallback_can_execute: bool = False

    def as_metadata(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @model_validator(mode="after")
    def _validate_recommendation_cannot_execute(self) -> ProviderRecommendation:
        if not self.metadata_only or self.can_execute or self.fallback_can_execute:
            raise ValueError("provider recommendation cannot execute or route.")
        _ensure_secret_free("provider recommendation", self.model_dump(mode="json"))
        return self


class ProviderRealTestStatus(SentinelModel):
    status: ProviderRealTestStatusKind = ProviderRealTestStatusKind.NOT_STARTED
    last_validated_model_id: str | None = None
    last_validated_backend_id: str | None = None
    success_evidence_commit: str | None = None
    provider_adapter_commit: str | None = None
    runtime_validation_commit: str | None = None
    provider_catalog_commit: str | None = None
    openai_compatible_base_commit: str | None = None
    diagnostic_outcomes: list[str] = Field(default_factory=list)
    requires_env_var: str | None = None


class ProviderBackendProfile(SentinelModel):
    backend_id: str
    family: ProviderFamily
    endpoint_template: str
    runtime: str
    supported_models: list[str] = Field(default_factory=list)
    supports_streaming: bool = False
    supports_json_mode: bool = False
    supports_json_schema: bool = False
    supports_tools: bool = False
    supports_reasoning_controls: bool = False
    supports_usage: bool = True
    usage_mapping: ProviderUsageMapping = Field(default_factory=ProviderUsageMapping)
    timeout_profile: ProviderTimeoutProfile = Field(default_factory=ProviderTimeoutProfile)
    retry_policy: ProviderRetryPolicy = Field(default_factory=ProviderRetryPolicy)
    reasoning_redaction_policy: ProviderReasoningRedactionPolicy = Field(
        default_factory=ProviderReasoningRedactionPolicy
    )
    request_policy_notes: list[str] = Field(default_factory=list)
    response_policy_notes: list[str] = Field(default_factory=list)

    def supports_model(self, model_id: str) -> bool:
        return model_id in set(self.supported_models)

    @model_validator(mode="after")
    def _validate_backend_metadata(self) -> ProviderBackendProfile:
        if not self.supported_models:
            raise ValueError("backend profile must explicitly list catalog-approved models.")
        _ensure_secret_free("provider backend profile", self.model_dump(mode="json"))
        return self


class ProviderCatalogEntry(SentinelModel):
    provider_id: str
    display_name: str
    family: ProviderFamily
    default_enabled: bool = False
    status: ProviderCatalogStatus = ProviderCatalogStatus.PLANNED
    backends: list[ProviderBackendProfile]
    credential_policy: ProviderCredentialPolicy
    capability_flags: ProviderCapabilityFlags
    recommendation: ProviderRecommendation | None = None
    real_test_status: ProviderRealTestStatus
    security_notes: list[str] = Field(default_factory=list)
    official_docs: list[str] = Field(default_factory=list)
    is_fake_provider: bool = False

    @model_validator(mode="after")
    def _validate_entry(self) -> ProviderCatalogEntry:
        if self.provider_id != self.provider_id.lower():
            raise ValueError("provider_id must be lowercase.")
        if self.is_fake_provider:
            raise ValueError("fake provider marker is not allowed.")
        if not self.backends:
            raise ValueError("provider catalog entry requires at least one backend.")
        if self.status is ProviderCatalogStatus.DISABLED and self.default_enabled:
            raise ValueError("disabled providers cannot be default enabled.")
        for backend in self.backends:
            if backend.family is not self.family:
                raise ValueError("backend family must match provider family.")
        _ensure_secret_free("provider catalog entry", self.model_dump(mode="json"))
        return self

    @property
    def supported_models(self) -> tuple[str, ...]:
        models: list[str] = []
        for backend in self.backends:
            models.extend(backend.supported_models)
        return tuple(dict.fromkeys(models))

    def supports_model(self, model_id: str) -> bool:
        return any(backend.supports_model(model_id) for backend in self.backends)


class ProviderCatalog:
    def __init__(self, *, entries: Iterable[ProviderCatalogEntry]) -> None:
        self._entries: dict[str, ProviderCatalogEntry] = {}
        for entry in entries:
            if entry.provider_id in self._entries:
                raise ValueError(f"duplicate provider catalog entry: {entry.provider_id}")
            if entry.is_fake_provider:
                raise ValueError("fake provider marker is not allowed.")
            self._entries[entry.provider_id] = entry
        _ensure_secret_free("provider catalog", self.safe_metadata())

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def get(self, provider_id: str) -> ProviderCatalogEntry:
        entry = self._entries.get(provider_id)
        if entry is None:
            raise LookupError(f"unknown provider: {provider_id}")
        return entry

    def require_enabled_provider(
        self,
        provider_id: str,
        *,
        model_id: str,
        enabled_provider_ids: set[str] | frozenset[str],
    ) -> ProviderCatalogEntry:
        entry = self.get(provider_id)
        if entry.provider_id not in enabled_provider_ids or entry.status is ProviderCatalogStatus.DISABLED:
            raise PermissionError(f"provider is disabled: {provider_id}")
        if not entry.supports_model(model_id):
            raise PermissionError("provider catalog cannot override the user-selected model.")
        return entry

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "providers": {
                provider_id: entry.model_dump(mode="json")
                for provider_id, entry in sorted(self._entries.items())
            }
        }


def _contains_secret_like_value(value: Any) -> bool:
    rendered = str(value)
    return any(pattern in rendered for pattern in _SECRET_LIKE_PATTERNS) or any(
        pattern.search(rendered) for pattern in _SECRET_LIKE_REGEXES
    )


def _ensure_secret_free(label: str, payload: Any) -> None:
    if _contains_secret_like_value(payload):
        raise ValueError(f"{label} contains secret-like metadata.")
