from __future__ import annotations

from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


NVIDIA_PROVIDER_ID = "nvidia"
NVIDIA_BACKEND_ID = "nvidia_openai_compatible_chat"
NVIDIA_DEFAULT_MODEL_ID = "minimaxai/minimax-m2.7"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_CREDENTIAL_ENV = "NVIDIA_API_KEY"


class NvidiaChatCompletionsProvider(OpenAICompatibleChatProvider):
    provider_id = NVIDIA_PROVIDER_ID
    backend_id = NVIDIA_BACKEND_ID

    def __init__(
        self,
        *,
        base_url: str = NVIDIA_BASE_URL,
        credential_env: str = NVIDIA_CREDENTIAL_ENV,
        default_model_id: str = NVIDIA_DEFAULT_MODEL_ID,
    ) -> None:
        profile = build_default_provider_catalog().get(NVIDIA_PROVIDER_ID).backends[0]
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id=NVIDIA_PROVIDER_ID,
                backend_id=NVIDIA_BACKEND_ID,
                base_url=base_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
                max_tokens_field="max_tokens",
            )
        )
