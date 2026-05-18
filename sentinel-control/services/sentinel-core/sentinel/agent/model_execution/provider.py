from __future__ import annotations

from typing import Protocol, runtime_checkable

from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy


@runtime_checkable
class RealModelProvider(Protocol):
    provider_id: str
    backend_id: str
    enabled: bool
    is_fake_provider: bool

    def execute(
        self,
        request: RealModelRequest,
        *,
        timeout: ModelTimeoutPolicy,
        credential: ProviderCredentialHandle,
    ) -> ProviderModelResponse | None:
        ...
