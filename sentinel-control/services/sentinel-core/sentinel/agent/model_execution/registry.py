from __future__ import annotations

from pydantic import Field

from sentinel.shared.models import SentinelModel, new_id


class ProviderCapabilityMetadata(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("provider_meta"))
    provider_id: str
    backend_id: str
    supported_models: list[str] = Field(default_factory=list)
    enabled: bool = False


class ModelProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, object] = {}

    def register(self, provider: object) -> None:
        provider_id = str(getattr(provider, "provider_id", ""))
        if not provider_id:
            raise ValueError("provider_id is required.")
        if bool(getattr(provider, "is_fake_provider", False)):
            raise ValueError("fake provider marker is not allowed.")
        if provider_id in self._providers:
            raise ValueError(f"duplicate provider_id registration: {provider_id}")
        self._providers[provider_id] = provider

    def get_enabled(self, provider_id: str, *, model_id: str) -> object:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise LookupError(f"unknown provider: {provider_id}")
        if not bool(getattr(provider, "enabled", False)):
            raise PermissionError(f"provider is disabled: {provider_id}")
        supported = tuple(getattr(provider, "supported_models", ()))
        if supported and model_id not in supported:
            raise PermissionError("provider cannot silently override the user-selected model.")
        return provider
