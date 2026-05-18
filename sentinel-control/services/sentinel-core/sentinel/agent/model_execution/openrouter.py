from __future__ import annotations

from sentinel.agent.model_execution.openai_compatible import (
    OpenAICompatibleChatProvider,
    OpenAICompatibleProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


OPENROUTER_PROVIDER_ID = "openrouter"
OPENROUTER_BACKEND_ID = "openrouter_chat_completions"
OPENROUTER_DEFAULT_MODEL_ID = "deepseek/deepseek-v4-flash:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CREDENTIAL_ENV = "OPENROUTER_API_KEY"


class OpenRouterChatCompletionsProvider(OpenAICompatibleChatProvider):
    provider_id = OPENROUTER_PROVIDER_ID
    backend_id = OPENROUTER_BACKEND_ID

    def __init__(
        self,
        *,
        base_url: str = OPENROUTER_BASE_URL,
        credential_env: str = OPENROUTER_CREDENTIAL_ENV,
        default_model_id: str = OPENROUTER_DEFAULT_MODEL_ID,
        reasoning_mode: str = "effort_high_exclude",
    ) -> None:
        profile = build_default_provider_catalog().get(OPENROUTER_PROVIDER_ID).backends[0]
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id=OPENROUTER_PROVIDER_ID,
                backend_id=OPENROUTER_BACKEND_ID,
                base_url=base_url,
                credential_env=credential_env,
                default_model_id=default_model_id,
                backend_profile=profile,
                max_tokens_field="max_completion_tokens",
                reasoning_request=_reasoning_payload(reasoning_mode),
            )
        )
        self.reasoning_mode = reasoning_mode


def _reasoning_payload(reasoning_mode: str) -> dict[str, object] | None:
    if reasoning_mode == "none":
        return None
    if reasoning_mode == "exclude_only":
        return {"exclude": True}
    return {"exclude": True, "effort": "high"}
