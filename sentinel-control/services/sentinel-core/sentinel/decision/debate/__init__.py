"""Deterministic debate engine for decide-before-execute."""

from sentinel.decision.debate.orchestrator import DebateOrchestrator
from sentinel.decision.debate.verdict import AgentOpinion, DebateResult

__all__ = ["AgentOpinion", "DebateOrchestrator", "DebateResult"]

