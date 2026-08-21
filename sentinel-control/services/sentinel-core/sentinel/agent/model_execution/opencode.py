from __future__ import annotations

from sentinel.agent.model_execution.openai_responses import (
    OpenAIResponsesProvider,
    OpenAIResponsesProviderConfig,
)
from sentinel.agent.model_execution.provider_profiles import build_default_provider_catalog


OPENCODE_PROVIDER_ID = "opencode"
OPENCODE_BACKEND_ID = "opencode_responses"
OPENCODE_DEFAULT_MODEL_ID = "muse-spark-1.2-contributor-free"
OPENCODE_RESPONSES_URL = "https://api.opencode.ai/v1/responses"
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
