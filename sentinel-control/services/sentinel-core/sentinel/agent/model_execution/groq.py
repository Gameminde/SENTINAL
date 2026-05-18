from __future__ import annotations

from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


GROQ_PROVIDER_ID = "groq"
GROQ_BACKEND_ID = "groq_openai_compatible_chat"
GROQ_DEFAULT_MODEL_ID = "openai/gpt-oss-20b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CREDENTIAL_ENV = "GROQ_API_KEY"


class GroqChatCompletionsProvider(OpenAICompatibleChatProvider):
    provider_id = GROQ_PROVIDER_ID
    backend_id = GROQ_BACKEND_ID

    def __init__(
        self,
        *,
        base_url: str = GROQ_BASE_URL,
        credential_env: str = GROQ_CREDENTIAL_ENV,
        default_model_id: str = GROQ_DEFAULT_MODEL_ID,
    ) -> None:
        profile = build_default_provider_catalog().get(GROQ_PROVIDER_ID).backends[0]
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id=GROQ_PROVIDER_ID,
                backend_id=GROQ_BACKEND_ID,
                base_url=base_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
                max_tokens_field="max_completion_tokens",
            )
        )
