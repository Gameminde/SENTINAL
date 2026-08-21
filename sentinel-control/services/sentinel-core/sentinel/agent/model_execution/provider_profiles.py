from __future__ import annotations

import os
from urllib.parse import urlparse

from sentinel.agent.model_execution.catalog import (
    ProviderBackendProfile,
    ProviderCapabilityFlags,
    ProviderCatalog,
    ProviderCatalogEntry,
    ProviderCatalogStatus,
    ProviderCredentialPolicy,
    ProviderFamily,
    ProviderRealTestStatus,
    ProviderRealTestStatusKind,
    ProviderReasoningRedactionPolicy,
    ProviderRecommendation,
    ProviderRetryPolicy,
    ProviderTimeoutProfile,
    ProviderUsageMapping,
)


def build_default_provider_catalog() -> ProviderCatalog:
    return ProviderCatalog(entries=_default_entries())


def _default_entries() -> list[ProviderCatalogEntry]:
    return [
        _entry(
            provider_id="groq",
            display_name="Groq",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="groq_openai_compatible_chat",
            endpoint="https://api.groq.com/openai/v1/chat/completions",
            env_var="GROQ_API_KEY",
            supported_models=["openai/gpt-oss-20b"],
            status=ProviderCatalogStatus.ACTIVE,
            real_status=ProviderRealTestStatusKind.SUCCESS_VALIDATED,
            last_model="openai/gpt-oss-20b",
            last_backend="groq_openai_compatible_chat",
            success_commit="187d251",
            provider_adapter_commit="187d251",
            runtime_validation_commit="9647993",
            provider_catalog_commit="7f0ddcb",
            openai_compatible_base_commit="4052be9",
            docs=["https://console.groq.com/docs/api-reference", "https://console.groq.com/docs/text-chat"],
            capability=ProviderCapabilityFlags(
                chat=True,
                streaming=True,
                json_mode=True,
                json_schema=True,
                tool_calling=True,
                reasoning_controls=True,
            ),
            recommendation=ProviderRecommendation(
                recommended_for=["skip-safe smoke tests", "validated provider regression"],
                avoid_for=["default routing", "silent fallback target"],
                latency_class="low",
                cost_class="low",
                reliability_class="proven",
                notes=["First SUCCESS_VALIDATED provider evidence; not runtime architecture."],
            ),
        ),
        _entry(
            provider_id="openrouter",
            display_name="OpenRouter",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="openrouter_chat_completions",
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            env_var="OPENROUTER_API_KEY",
            supported_models=[
                "deepseek/deepseek-v4-flash:free",
                "z-ai/glm-5.2",
                "moonshotai/kimi-k2.7-code",
                "qwen/qwen3.5-plus-02-15",
                "nvidia/minimaxai/minimax-m3",
            ],
            status=ProviderCatalogStatus.DIAGNOSTIC,
            real_status=ProviderRealTestStatusKind.DIAGNOSTIC_ONLY,
            diagnostic_outcomes=["RATE_LIMIT", "TIMEOUT", "PROVIDER_ERROR"],
            docs=["https://openrouter.ai/docs/api-reference/chat-completion"],
            timeout=ProviderTimeoutProfile(read_timeout_seconds=30.0, total_timeout_seconds=35.0),
            recommendation=ProviderRecommendation(
                recommended_for=["explicit C6 provider mesh experiments", "diagnostic gateway research"],
                avoid_for=["openrouter/auto", "silent fallback", "unlisted model routing"],
                reliability_class="diagnostic",
                notes=["C6 mesh models are explicitly pinned; openrouter/auto remains forbidden for first proofs."],
            ),
        ),
        _entry(
            provider_id="nvidia",
            display_name="NVIDIA NIM / Integrate",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="nvidia_openai_compatible_chat",
            endpoint="https://integrate.api.nvidia.com/v1/chat/completions",
            env_var="NVIDIA_API_KEY",
            supported_models=["minimaxai/minimax-m3", "minimaxai/minimax-m2.7"],
            status=ProviderCatalogStatus.DIAGNOSTIC,
            real_status=ProviderRealTestStatusKind.DIAGNOSTIC_ONLY,
            diagnostic_outcomes=["TIMEOUT", "PRODUCT_ROUTE_NOT_YET_RUN"],
            docs=[
                "https://build.nvidia.com/minimaxai/minimax-m3",
                "https://docs.nvidia.com/nim/large-language-models/latest/reference/api-reference.html",
            ],
            capability=ProviderCapabilityFlags(
                chat=True,
                streaming=False,
                json_mode=False,
                json_schema=False,
                tool_calling=False,
                server_side_tools=False,
                reasoning_controls=False,
            ),
            timeout=ProviderTimeoutProfile(read_timeout_seconds=120.0, total_timeout_seconds=150.0),
            recommendation=ProviderRecommendation(
                recommended_for=["long-timeout diagnostics", "explicit MiniMax M3 product-route experiments"],
                avoid_for=["short smoke tests"],
                reliability_class="diagnostic",
                notes=["Hosted diagnostics observed timeout; local NIM policy remains separate."],
            ),
        ),
        _entry(
            provider_id="opencode",
            display_name="OpenCode Zen",
            family=ProviderFamily.OPENAI_NATIVE,
            backend_id="opencode_responses",
            endpoint="https://api.opencode.ai/v1/responses",
            env_var="OPENCODE_API_KEY",
            supported_models=["muse-spark-1.2-contributor-free"],
            status=ProviderCatalogStatus.DIAGNOSTIC,
            real_status=ProviderRealTestStatusKind.DIAGNOSTIC_ONLY,
            diagnostic_outcomes=["PRODUCT_ROUTE_NOT_YET_RUN"],
            docs=["https://opencode.ai/docs/zen/"],
            capability=ProviderCapabilityFlags(
                responses=True,
                streaming=False,
                json_mode=False,
                json_schema=False,
                tool_calling=False,
                server_side_tools=False,
                reasoning_controls=False,
            ),
            timeout=ProviderTimeoutProfile(read_timeout_seconds=60.0, total_timeout_seconds=70.0),
            recommendation=ProviderRecommendation(
                recommended_for=["explicit free-model product-route experiments", "provider diversity diagnostics"],
                avoid_for=["silent fallback", "unlisted paid Muse model routing"],
                cost_class="free",
                reliability_class="diagnostic",
                notes=[
                    "Use explicit free model ids; the standard Muse Spark model may require billing.",
                    "Responses endpoint only; provider output still passes through Sentinel Intent Bridge.",
                ],
            ),
        ),
        _entry(
            provider_id="opencode_chat",
            display_name="OpenCode Chat Completions",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="opencode_chat_completions",
            endpoint="https://api.opencode.ai/v1/chat/completions",
            env_var="OPENCODE_API_KEY",
            supported_models=["x-preview-f-free"],
            status=ProviderCatalogStatus.DIAGNOSTIC,
            real_status=ProviderRealTestStatusKind.DIAGNOSTIC_ONLY,
            diagnostic_outcomes=["PRODUCT_ROUTE_NOT_YET_RUN"],
            docs=["https://opencode.ai/docs/zen/"],
            capability=ProviderCapabilityFlags(
                chat=True,
                streaming=False,
                json_mode=False,
                json_schema=False,
                tool_calling=False,
                server_side_tools=False,
                reasoning_controls=False,
            ),
            timeout=ProviderTimeoutProfile(read_timeout_seconds=60.0, total_timeout_seconds=70.0),
            recommendation=ProviderRecommendation(
                recommended_for=["explicit OpenCode free chat model experiments"],
                avoid_for=["silent fallback", "unverified display-name routing"],
                cost_class="free",
                reliability_class="diagnostic",
                notes=[
                    "OpenCode model listing exposes x-preview-f-free.",
                    "Public display names such as Ox Alpha Free are not used as authority unless the API exposes a matching id.",
                ],
            ),
        ),
        _entry(
            provider_id="aliyun_dashscope",
            display_name="Aliyun DashScope / Model Studio",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="aliyun_openai_compatible_chat",
            endpoint=_aliyun_dashscope_endpoint(),
            env_var="SENTINEL_CERT_MODEL_API_KEY",
            supported_models=[
                "qwen-plus",
                "qwen3.7-plus",
                "qwen3.7-max",
                "qwen3-coder-plus",
                "qwen3-coder-next",
                "deepseek-v4-pro",
                "glm-5.2",
            ],
            reasoning_disable_fields={"enable_thinking": False, "reasoning_effort": "none"},
            status=ProviderCatalogStatus.DIAGNOSTIC,
            real_status=ProviderRealTestStatusKind.DIAGNOSTIC_ONLY,
            diagnostic_outcomes=["PRODUCT_ROUTE_NOT_YET_RUN"],
            docs=["https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope"],
            timeout=ProviderTimeoutProfile(read_timeout_seconds=60.0, total_timeout_seconds=70.0),
            capability=ProviderCapabilityFlags(
                chat=True,
                streaming=False,
                json_mode=False,
                json_schema=False,
                tool_calling=False,
                server_side_tools=False,
            ),
            recommendation=ProviderRecommendation(
                recommended_for=["explicit Aliyun-hosted DeepSeek V4 Pro product-route experiments"],
                avoid_for=["default routing", "silent fallback target", "provider-native tools"],
                reliability_class="diagnostic",
                notes=[
                    "OpenAI-compatible request shape on Aliyun/DashScope infrastructure.",
                    "Qwen model IDs follow the official Model Studio OpenAI-compatible catalog.",
                    "Endpoint override is restricted to Aliyun/DashScope hosts and must be explicit.",
                ],
            ),
        ),
        _entry(
            provider_id="deepseek",
            display_name="DeepSeek",
            family=ProviderFamily.DEEPSEEK_COMPATIBLE,
            backend_id="deepseek_chat_completions",
            endpoint="https://api.deepseek.com/chat/completions",
            env_var="DEEPSEEK_API_KEY",
            supported_models=["deepseek-chat", "deepseek-reasoner"],
            docs=["https://api-docs.deepseek.com/api/create-chat-completion"],
            reasoning_fields=["reasoning_content", "reasoning_tokens"],
            recommendation=ProviderRecommendation(
                recommended_for=["first new hosted provider after catalog"],
                avoid_for=["raw reasoning durability"],
                reliability_class="unknown",
                notes=["OpenAI-compatible shape with explicit reasoning redaction requirements."],
            ),
        ),
        _entry(
            provider_id="mistral",
            display_name="Mistral",
            family=ProviderFamily.MISTRAL_NATIVE_OR_COMPATIBLE,
            backend_id="mistral_chat_completions",
            endpoint="https://api.mistral.ai/v1/chat/completions",
            env_var="MISTRAL_API_KEY",
            supported_models=["mistral-small-latest", "mistral-large-latest"],
            docs=["https://docs.mistral.ai/api"],
            recommendation=ProviderRecommendation(
                recommended_for=["structured output provider expansion"],
                avoid_for=["implicit tool execution"],
                reliability_class="unknown",
            ),
        ),
        _entry(
            provider_id="xai",
            display_name="xAI",
            family=ProviderFamily.XAI_COMPATIBLE_OR_NATIVE,
            backend_id="xai_chat_completions",
            endpoint="https://api.x.ai/v1/chat/completions",
            env_var="XAI_API_KEY",
            supported_models=["grok-4", "grok-3"],
            docs=["https://docs.x.ai/docs/guides/chat-completions"],
            timeout=ProviderTimeoutProfile(read_timeout_seconds=60.0, total_timeout_seconds=70.0),
        ),
        _entry(
            provider_id="openai",
            display_name="OpenAI Responses",
            family=ProviderFamily.OPENAI_NATIVE,
            backend_id="openai_responses",
            endpoint="https://api.openai.com/v1/responses",
            env_var="OPENAI_API_KEY",
            supported_models=["gpt-5.4", "gpt-5.4-mini", "gpt-oss-20b"],
            docs=["https://platform.openai.com/docs/api-reference/responses/create"],
            capability=ProviderCapabilityFlags(responses=True, streaming=True, json_schema=True, tool_calling=True),
        ),
        _entry(
            provider_id="openai_chat",
            display_name="OpenAI Chat Completions",
            family=ProviderFamily.OPENAI_COMPATIBLE_CHAT,
            backend_id="openai_chat_completions",
            endpoint="https://api.openai.com/v1/chat/completions",
            env_var="OPENAI_API_KEY",
            supported_models=["gpt-5.4", "gpt-5.4-mini"],
            docs=["https://platform.openai.com/docs/api-reference/chat/create"],
        ),
        _entry(
            provider_id="anthropic",
            display_name="Anthropic Claude",
            family=ProviderFamily.ANTHROPIC_MESSAGES_NATIVE,
            backend_id="anthropic_messages",
            endpoint="https://api.anthropic.com/v1/messages",
            env_var="ANTHROPIC_API_KEY",
            supported_models=["claude-sonnet-4-5", "claude-haiku-4-5"],
            docs=["https://docs.anthropic.com/en/api/messages"],
            capability=ProviderCapabilityFlags(messages=True, streaming=True, json_schema=True, tool_calling=True),
            reasoning_fields=["thinking", "thinking_blocks"],
        ),
        _entry(
            provider_id="google_gemini",
            display_name="Google Gemini",
            family=ProviderFamily.GEMINI_NATIVE,
            backend_id="gemini_generate_content",
            endpoint="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            env_var="GEMINI_API_KEY",
            supported_models=["gemini-2.5-pro", "gemini-2.5-flash"],
            docs=["https://ai.google.dev/gemini-api/docs/text-generation"],
            capability=ProviderCapabilityFlags(generate_content=True, streaming=True, json_schema=True, tool_calling=True),
            reasoning_fields=["thought", "thought_signature"],
        ),
        _entry(
            provider_id="cohere",
            display_name="Cohere",
            family=ProviderFamily.COHERE_NATIVE,
            backend_id="cohere_chat_v2",
            endpoint="https://api.cohere.com/v2/chat",
            env_var="COHERE_API_KEY",
            supported_models=["command-a-03-2025", "command-r7b-12-2024"],
            docs=["https://docs.cohere.com/v2/reference/chat"],
            capability=ProviderCapabilityFlags(messages=True, streaming=True, json_schema=True, tool_calling=True),
            reasoning_fields=["thinking"],
        ),
        _entry(
            provider_id="ollama",
            display_name="Ollama",
            family=ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
            backend_id="ollama_openai_compatible_chat",
            endpoint="http://localhost:11434/v1/chat/completions",
            env_var=None,
            supported_models=["llama3.2", "qwen2.5"],
            status=ProviderCatalogStatus.LOCAL_ONLY,
            docs=["https://docs.ollama.com/openai"],
            capability=ProviderCapabilityFlags(
                chat=True,
                streaming=True,
                json_mode=True,
                tool_calling=True,
                reasoning_controls=True,
                local_runtime=True,
            ),
            credential_source_type="local_none",
            required_for_real_call=False,
        ),
        _entry(
            provider_id="lmstudio",
            display_name="LM Studio",
            family=ProviderFamily.LOCAL_OPENAI_COMPATIBLE,
            backend_id="lmstudio_openai_compatible_chat",
            endpoint="http://localhost:1234/v1/chat/completions",
            env_var="LMSTUDIO_API_KEY",
            supported_models=["local/user-selected"],
            status=ProviderCatalogStatus.LOCAL_ONLY,
            docs=["https://lmstudio.ai/docs/app/api/endpoints/openai"],
            capability=ProviderCapabilityFlags(
                chat=True,
                responses=True,
                streaming=True,
                json_schema=True,
                tool_calling=True,
                local_runtime=True,
            ),
            credential_source_type="local_none",
            required_for_real_call=False,
        ),
    ]


def _aliyun_dashscope_endpoint() -> str:
    base_url = os.environ.get(
        "SENTINEL_ALIYUN_DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ).rstrip("/")
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise ValueError("aliyun dashscope endpoint must use https")
    if not (
        host == "dashscope.aliyuncs.com"
        or host.endswith(".dashscope.aliyuncs.com")
        or host.endswith(".maas.aliyuncs.com")
    ):
        raise ValueError("aliyun dashscope endpoint host not allowed")
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def _entry(
    *,
    provider_id: str,
    display_name: str,
    family: ProviderFamily,
    backend_id: str,
    endpoint: str,
    env_var: str | None,
    supported_models: list[str],
    docs: list[str],
    status: ProviderCatalogStatus = ProviderCatalogStatus.PLANNED,
    real_status: ProviderRealTestStatusKind = ProviderRealTestStatusKind.NOT_STARTED,
    last_model: str | None = None,
    last_backend: str | None = None,
    success_commit: str | None = None,
    provider_adapter_commit: str | None = None,
    runtime_validation_commit: str | None = None,
    provider_catalog_commit: str | None = None,
    openai_compatible_base_commit: str | None = None,
    diagnostic_outcomes: list[str] | None = None,
    capability: ProviderCapabilityFlags | None = None,
    timeout: ProviderTimeoutProfile | None = None,
    recommendation: ProviderRecommendation | None = None,
    reasoning_fields: list[str] | None = None,
    reasoning_disable_fields: dict[str, object] | None = None,
    credential_source_type: str = "env",
    required_for_real_call: bool = True,
) -> ProviderCatalogEntry:
    backend = ProviderBackendProfile(
        backend_id=backend_id,
        family=family,
        endpoint_template=endpoint,
        runtime=_runtime_for_family(family),
        supported_models=supported_models,
        supports_streaming=bool(capability.streaming if capability else True),
        supports_json_mode=bool(capability.json_mode if capability else True),
        supports_json_schema=bool(capability.json_schema if capability else False),
        supports_tools=bool(capability.tool_calling if capability else True),
        supports_reasoning_controls=bool(capability.reasoning_controls if capability else True),
        usage_mapping=_usage_mapping_for_family(family),
        timeout_profile=timeout or ProviderTimeoutProfile(),
        retry_policy=ProviderRetryPolicy(max_attempts=1, retryable_outcomes=[]),
        reasoning_redaction_policy=ProviderReasoningRedactionPolicy(
            raw_reasoning_fields=reasoning_fields or ProviderReasoningRedactionPolicy().raw_reasoning_fields,
            request_reasoning_disable_fields=reasoning_disable_fields or {},
        ),
    )
    return ProviderCatalogEntry(
        provider_id=provider_id,
        display_name=display_name,
        family=family,
        status=status,
        backends=[backend],
        credential_policy=ProviderCredentialPolicy(
            credential_env_var=env_var,
            credential_source_type=credential_source_type,
            required_for_real_call=required_for_real_call,
        ),
        capability_flags=capability or ProviderCapabilityFlags(chat=True, streaming=True, tool_calling=True),
        recommendation=recommendation,
        real_test_status=ProviderRealTestStatus(
            status=real_status,
            last_validated_model_id=last_model,
            last_validated_backend_id=last_backend,
            success_evidence_commit=success_commit,
            provider_adapter_commit=provider_adapter_commit,
            runtime_validation_commit=runtime_validation_commit,
            provider_catalog_commit=provider_catalog_commit,
            openai_compatible_base_commit=openai_compatible_base_commit,
            diagnostic_outcomes=diagnostic_outcomes or [],
            requires_env_var=env_var,
        ),
        security_notes=[
            "metadata only",
            "no tool or organ execution",
            "no raw prompt, response, reasoning, or key durability",
        ],
        official_docs=docs,
    )


def _runtime_for_family(family: ProviderFamily) -> str:
    if family is ProviderFamily.OPENAI_NATIVE:
        return "responses"
    if family is ProviderFamily.ANTHROPIC_MESSAGES_NATIVE:
        return "messages"
    if family is ProviderFamily.GEMINI_NATIVE:
        return "generate_content"
    return "chat_completions"


def _usage_mapping_for_family(family: ProviderFamily) -> ProviderUsageMapping:
    if family is ProviderFamily.ANTHROPIC_MESSAGES_NATIVE:
        return ProviderUsageMapping(input_tokens_path="usage.input_tokens", output_tokens_path="usage.output_tokens")
    if family is ProviderFamily.GEMINI_NATIVE:
        return ProviderUsageMapping(
            input_tokens_path="usageMetadata.promptTokenCount",
            output_tokens_path="usageMetadata.candidatesTokenCount",
            total_tokens_path="usageMetadata.totalTokenCount",
        )
    if family is ProviderFamily.COHERE_NATIVE:
        return ProviderUsageMapping(input_tokens_path="usage.tokens.input_tokens", output_tokens_path="usage.tokens.output_tokens")
    return ProviderUsageMapping(
        input_tokens_path="usage.prompt_tokens",
        output_tokens_path="usage.completion_tokens",
        total_tokens_path="usage.total_tokens",
    )
