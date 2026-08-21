from __future__ import annotations

from sentinel.agent.model_execution.openai_responses import (
    OpenAIResponsesProvider,
    OpenAIResponsesProviderConfig,
)
from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


OPENCODE_PROVIDER_ID = "opencode"
OPENCODE_CHAT_PROVIDER_ID = "opencode_chat"
OPENCODE_BACKEND_ID = "opencode_responses"
OPENCODE_CHAT_BACKEND_ID = "opencode_chat_completions"
OPENCODE_DEFAULT_MODEL_ID = "muse-spark-1.2-contributor-free"
OPENCODE_CHAT_DEFAULT_MODEL_ID = "x-preview-f-free"
OPENCODE_RESPONSES_URL = "https://api.opencode.ai/v1/responses"
OPENCODE_CHAT_BASE_URL = "https://api.opencode.ai/v1"
OPENCODE_CREDENTIAL_ENV = "OPENCODE_API_KEY"


class OpenCodeResponsesProvider(OpenAIResponsesProvider):
    provider_id = OPENCODE_PROVIDER_ID
    backend_id = OPENCODE_BACKEND_ID

    def __init__(
        self,
        *,
        endpoint_url: str = OPENCODE_RESPONSES_URL,
        credential_env: str = OPENCODE_CREDENTIAL_ENV,
        default_model_id: str = OPENCODE_DEFAULT_MODEL_ID,
    ) -> None:
        profile = build_default_provider_catalog().get(OPENCODE_PROVIDER_ID).backends[0]
        super().__init__(
            config=OpenAIResponsesProviderConfig(
                provider_id=OPENCODE_PROVIDER_ID,
                backend_id=OPENCODE_BACKEND_ID,
                endpoint_url=endpoint_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
            )
        )


class OpenCodeChatCompletionsProvider(OpenAICompatibleChatProvider):
    provider_id = OPENCODE_CHAT_PROVIDER_ID
    backend_id = OPENCODE_CHAT_BACKEND_ID

    def __init__(
        self,
        *,
        base_url: str = OPENCODE_CHAT_BASE_URL,
        credential_env: str = OPENCODE_CREDENTIAL_ENV,
        default_model_id: str = OPENCODE_CHAT_DEFAULT_MODEL_ID,
    ) -> None:
        profile = next(
            backend
            for backend in build_default_provider_catalog().get(OPENCODE_CHAT_PROVIDER_ID).backends
            if backend.backend_id == OPENCODE_CHAT_BACKEND_ID
        )
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id=OPENCODE_CHAT_PROVIDER_ID,
                backend_id=OPENCODE_CHAT_BACKEND_ID,
                base_url=base_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
                max_tokens_field="max_tokens",
            )
        )
