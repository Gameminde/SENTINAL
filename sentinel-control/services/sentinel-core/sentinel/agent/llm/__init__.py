"""Bounded LLM cortex contracts.

The LLM layer may draft reasoning and tool intentions. It does not create
mission authority and does not execute tools directly.
"""

from sentinel.agent.llm.context_pack import (
    ContextPack,
    ContextPackActionIntent,
    ContextPackAssembler,
    ContextPackAuthorityBoundary,
    ContextPackBrowserEvidenceSummary,
    ContextPackBudget,
    ContextPackCitation,
    ContextPackCurrentState,
    ContextPackHypothesis,
    ContextPackPromptInjectionFlag,
    ContextPackSourceQualityFlag,
    ContextPackStableRef,
    ContextPackValidationResult,
    ContextPackValidator,
    hash_context_pack_payload,
)
from sentinel.agent.llm.interface import (
    BrowserPlannerRole,
    BrowserVerifierRole,
    LLMReasoningOutput,
    LLMRole,
    LLMVerificationOutput,
)
from sentinel.agent.llm.role_loop import (
    LLMRoleContract,
    LLMRoleId,
    LLMRoleInputFrame,
    LLMRoleLoopOrchestrator,
    LLMRoleLoopPlan,
    LLMRoleLoopResult,
    LLMRoleOutput,
    RoleLoopBudgetSummary,
    RoleLoopReceipt,
    RoleLoopStatus,
    build_default_llm_role_contracts,
)
from sentinel.agent.llm.tool_intent_compiler import (
    CompiledToolIntent,
    ToolIntentCompilationResult,
    ToolIntentCompilationStage,
    ToolIntentCompilationStatus,
    ToolIntentCompiler,
)

__all__ = [
    "BrowserPlannerRole",
    "BrowserVerifierRole",
    "CompiledToolIntent",
    "ContextPack",
    "ContextPackActionIntent",
    "ContextPackAssembler",
    "ContextPackAuthorityBoundary",
    "ContextPackBrowserEvidenceSummary",
    "ContextPackBudget",
    "ContextPackCitation",
    "ContextPackCurrentState",
    "ContextPackHypothesis",
    "ContextPackPromptInjectionFlag",
    "ContextPackSourceQualityFlag",
    "ContextPackStableRef",
    "ContextPackValidationResult",
    "ContextPackValidator",
    "LLMReasoningOutput",
    "LLMRole",
    "LLMRoleContract",
    "LLMRoleId",
    "LLMRoleInputFrame",
    "LLMRoleLoopOrchestrator",
    "LLMRoleLoopPlan",
    "LLMRoleLoopResult",
    "LLMRoleOutput",
    "LLMVerificationOutput",
    "RoleLoopBudgetSummary",
    "RoleLoopReceipt",
    "RoleLoopStatus",
    "ToolIntentCompilationResult",
    "ToolIntentCompilationStage",
    "ToolIntentCompilationStatus",
    "ToolIntentCompiler",
    "build_default_llm_role_contracts",
    "hash_context_pack_payload",
]
