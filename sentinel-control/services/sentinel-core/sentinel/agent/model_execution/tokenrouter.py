from __future__ import annotations

from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


TOKENROUTER_PROVIDER_ID = "tokenrouter"
TOKENROUTER_BACKEND_ID = "tokenrouter_chat_completions"
TOKENROUTER_DEFAULT_MODEL_ID = "qwen/qwen3.8-max-free"
TOKENROUTER_BASE_URL = "https://api.tokenrouter.com/v1"
TOKENROUTER_CREDENTIAL_ENV = "TOKENROUTER_API_KEY"


class TokenRouterChatCompletionsProvider(OpenAICompatibleChatProvider):
    provider_id = TOKENROUTER_PROVIDER_ID
    backend_id = TOKENROUTER_BACKEND_ID

    def __init__(
        self,
        *,
        base_url: str = TOKENROUTER_BASE_URL,
        credential_env: str = TOKENROUTER_CREDENTIAL_ENV,
        default_model_id: str = TOKENROUTER_DEFAULT_MODEL_ID,
    ) -> None:
        profile = build_default_provider_catalog().get(TOKENROUTER_PROVIDER_ID).backends[0]
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id=TOKENROUTER_PROVIDER_ID,
                backend_id=TOKENROUTER_BACKEND_ID,
                base_url=base_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
                max_tokens_field="max_tokens",
            )
        )
