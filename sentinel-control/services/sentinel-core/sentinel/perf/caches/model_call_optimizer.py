"""ModelCallOptimizer — runtime/model/backend planner.

Task 6.5 / sentinel-performance-runtime-foundation.

Requirements: 9.3, 11.6.

Scope summary
-------------

This module provides :class:`ModelCallOptimizer`, a deterministic
*structural* planner. Given an :class:`LLMDecisionFrame` and an
optional :class:`TokenLedger`, it returns a :class:`ModelCallPlan`
describing:

* which model id and backend to use,
* which runtime mode (``streaming``, ``batch``, ``completion``) to
  request,
* whether the prefix-reuse path through
  :class:`PromptFrameCache.reuse_prefix` should be engaged,
* the stable-prefix hash to key that reuse on,
* the evidence-card delta count, and
* an estimated input-token count.

The optimizer is **not** an LLM: it does not call any model and does
not perform retrieval. It reads the frame and ledger and emits a
plan. The wiring layer (Task 6.11) is responsible for handing the
plan to the cache and for emitting any cache or budget events around
it; this module is event-bus-free by design.

Determinism (Requirement 9.3)
-----------------------------

For a fixed ``(frame, ledger)`` pair the planner returns an
identical :class:`ModelCallPlan` on every invocation. There is no
randomness, no clock read, and no mutable state on the optimizer
itself; the only state is the immutable ``default_model_id`` and
``default_backend`` constructor arguments. The
:func:`_compute_stable_prefix_hash` helper hashes a canonical JSON
form of the mission card, authority card, selected tool surface, and
required output schema (sorted keys, ASCII escapes), so equal frames
always produce equal prefix hashes regardless of dict ordering.

Read-only contract
------------------

The optimizer never mutates ``frame`` or ``ledger``. ``frame`` is a
frozen-style pydantic model in practice, but even where pydantic
permits in-place writes the optimizer treats it as read-only. The
ledger is consulted via ``total_tokens()`` only — entries are not
indexed or rewritten.

Token estimation (Requirements 9.3, 11.6)
-----------------------------------------

Token estimation follows the same resolution order as
:func:`sentinel.perf.caches.token_budget_governor._estimate_frame_tokens`:

1. ``frame.prompt_tokens`` if present and int-coercible,
2. else ``frame.token_count`` (the canonical
   :class:`LLMDecisionFrame` field, populated by
   :class:`PromptBudgetAllocator.estimate_frame_tokens`),
3. else canonical ``model_dump`` JSON length divided by 4,
4. else ``str(frame)`` length divided by 4.

The estimate is clamped to a non-negative integer in every case.

Long-context model selection (Requirement 11.6)
-----------------------------------------------

When the estimated input-token count exceeds
:data:`LONG_CONTEXT_TOKEN_THRESHOLD` (100,000), the planner overrides
``default_model_id`` with a long-context model id
(:data:`LONG_CONTEXT_MODEL_ID`). The override is structural — the
planner does not "swap" the user's selected model, it only reports
the recommendation in the plan. Wiring code (Task 6.11) decides
whether to honour the recommendation; the user-selected model
contract enforced by :class:`UserModelContract` is unaffected.

Backend selection
-----------------

Backend is derived from ``model_id`` prefix:

* ``gpt-*`` → ``"openai"``,
* ``claude-*`` → ``"anthropic"``,
* anything else → ``default_backend`` (constructor argument).

The match is case-insensitive on the model-id prefix only; the
returned ``model_id`` itself preserves the original casing.

Runtime selection
-----------------

Runtime defaults to ``"completion"``. If the frame (or, where
present, the underlying model definition reachable through it)
exposes a truthy ``streaming`` flag, the runtime is set to
``"streaming"``. The optimizer does not attempt to read a side
channel for a ``"batch"`` mode — that mode is reserved for the
batch-execution planner in Phase D and is never selected from a
single-frame plan.

Prefix-reuse strategy (Requirement 9.3)
---------------------------------------

If ``frame`` exposes a ``stable_prefix_hash`` attribute the planner
uses it directly. Otherwise the planner computes one as the SHA-256
hex of the canonical JSON form of
``(mission_card, authority_card, selected_tool_surface,
required_output_schema)`` — exactly the slice of the frame that is
*stable* across consecutive evidence-only deltas. ``top_k_evidence``
and ``progress_card`` are excluded from the prefix hash because they
are precisely what an evidence-delta call would change.

``use_prefix_reuse`` is set to ``True`` whenever a stable prefix hash
is available (i.e. always, after the computation above). The
``evidence_delta_count`` field carries the size of the frame's
evidence set; the prompt-frame cache (Task 6.2) is responsible for
the actual delta math when ``reuse_prefix`` is invoked.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ConfigDict, Field

from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.shared.models import SentinelModel

__all__ = [
    "BACKEND_ANTHROPIC",
    "BACKEND_OPENAI",
    "DEFAULT_BACKEND",
    "DEFAULT_MODEL_ID",
    "LONG_CONTEXT_MODEL_ID",
    "LONG_CONTEXT_TOKEN_THRESHOLD",
    "ModelCallOptimizer",
    "ModelCallPlan",
    "RUNTIME_BATCH",
    "RUNTIME_COMPLETION",
    "RUNTIME_STREAMING",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


DEFAULT_MODEL_ID: str = "gpt-4o-mini"
"""Default short-context model id when no other signal applies."""

DEFAULT_BACKEND: str = "openai"
"""Default backend when neither model-id prefix nor signal applies."""

BACKEND_OPENAI: str = "openai"
BACKEND_ANTHROPIC: str = "anthropic"

RUNTIME_STREAMING: str = "streaming"
RUNTIME_BATCH: str = "batch"
RUNTIME_COMPLETION: str = "completion"

LONG_CONTEXT_TOKEN_THRESHOLD: int = 100_000
"""Token count above which the planner recommends a long-context model."""

LONG_CONTEXT_MODEL_ID: str = "gpt-4o"
"""Long-context model id used when the estimated input exceeds
:data:`LONG_CONTEXT_TOKEN_THRESHOLD`. Backend resolves to
:data:`BACKEND_OPENAI` via the ``gpt-`` prefix rule."""

# Rationale tags (short, machine-readable; no user content)
_RATIONALE_DEFAULT: str = "default_model_short_context"
_RATIONALE_LONG_CONTEXT: str = "long_context_due_to_token_count"
_RATIONALE_PREFIX_REUSE: str = "prefix_reuse_enabled"


# ---------------------------------------------------------------------------
# Token estimation helper
# ---------------------------------------------------------------------------


def _estimate_frame_tokens(frame: Any) -> int:
    """Return a non-negative integer estimate of ``frame``'s tokens.

    Mirrors
    :func:`sentinel.perf.caches.token_budget_governor._estimate_frame_tokens`
    so the planner and the budget governor agree on a single token
    estimate for the same frame. The resolution order is documented
    in the module docstring above.
    """

    candidate = getattr(frame, "prompt_tokens", None)
    if candidate is not None:
        try:
            return max(0, int(candidate))
        except (TypeError, ValueError):
            pass

    candidate = getattr(frame, "token_count", None)
    if candidate is not None:
        try:
            return max(0, int(candidate))
        except (TypeError, ValueError):
            pass

    model_dump = getattr(frame, "model_dump", None)
    if callable(model_dump):
        try:
            payload = model_dump(mode="json")
        except TypeError:
            payload = model_dump()
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        )
        return max(0, len(canonical) // 4)

    return max(0, len(str(frame)) // 4)


# ---------------------------------------------------------------------------
# Stable-prefix hash helper
# ---------------------------------------------------------------------------


def _compute_stable_prefix_hash(frame: Any) -> str | None:
    """Return SHA-256 hex of the frame's evidence-independent slice.

    Hashes a canonical JSON form of
    ``(mission_card, authority_card, selected_tool_surface,
    required_output_schema)`` — the slice of an
    :class:`LLMDecisionFrame` that does not change when only the
    evidence delta changes between two consecutive frames
    (Requirement 9.3). Returns ``None`` only if none of the four
    fields are available on ``frame``; in that case the planner falls
    back to disabling prefix reuse.
    """

    payload: dict[str, Any] = {}
    for field in (
        "mission_card",
        "authority_card",
        "selected_tool_surface",
        "required_output_schema",
    ):
        if hasattr(frame, field):
            payload[field] = getattr(frame, field)

    if not payload:
        return None

    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# ModelCallPlan
# ---------------------------------------------------------------------------


class ModelCallPlan(SentinelModel):
    """Frozen plan describing a single model call.

    Carries integer counters, fixed string tags, and SHA-256 hashes
    only — no frame body, no evidence content, no raw user input, no
    secret. Frozen so downstream consumers cannot mutate the plan
    after the optimizer hands it off.

    Fields
    ------

    * ``model_id``                — recommended model identifier.
    * ``backend``                 — ``"openai"`` / ``"anthropic"`` /
                                    fallback ``default_backend``.
    * ``runtime``                 — ``"streaming"`` / ``"batch"`` /
                                    ``"completion"``.
    * ``use_prefix_reuse``        — ``True`` iff a stable prefix hash
                                    is available and prefix reuse is
                                    recommended.
    * ``stable_prefix_hash``      — SHA-256 hex of the frame's
                                    evidence-independent slice, or
                                    ``None``.
    * ``evidence_delta_count``    — number of evidence cards in the
                                    frame; consumers compute the true
                                    delta against their own prefix
                                    state.
    * ``estimated_input_tokens``  — non-negative integer estimate.
    * ``rationale``               — short, static, machine-readable tag.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    backend: str
    runtime: str
    use_prefix_reuse: bool
    stable_prefix_hash: str | None
    evidence_delta_count: int = Field(ge=0)
    estimated_input_tokens: int = Field(ge=0)
    rationale: str


# ---------------------------------------------------------------------------
# ModelCallOptimizer
# ---------------------------------------------------------------------------


class ModelCallOptimizer:
    """Selects runtime/model/backend and prefix-reuse strategy.

    Requirements: 9.3, 11.6.

    The optimizer is a pure planner: ``plan`` is a function of its
    inputs and the constructor's ``default_model_id`` /
    ``default_backend``. It does not touch the EventBus, does not
    perform retrieval, does not call any model, and does not maintain
    per-call state. Wiring code (Task 6.11) is responsible for any
    event emission around the planner.
    """

    def __init__(
        self,
        *,
        default_model_id: str = DEFAULT_MODEL_ID,
        default_backend: str = DEFAULT_BACKEND,
    ) -> None:
        if not default_model_id:
            raise ValueError("ModelCallOptimizer.default_model_id must be non-empty")
        if not default_backend:
            raise ValueError("ModelCallOptimizer.default_backend must be non-empty")
        self._default_model_id = default_model_id
        self._default_backend = default_backend

    # ------------------------------------------------------------------
    # Read-only accessors (for tests + diagnostics)
    # ------------------------------------------------------------------

    @property
    def default_model_id(self) -> str:
        return self._default_model_id

    @property
    def default_backend(self) -> str:
        return self._default_backend

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, frame: LLMDecisionFrame, ledger: Any | None = None) -> ModelCallPlan:
        """Compute a :class:`ModelCallPlan` for ``frame`` (+ ``ledger``).

        Determinism: equal ``(frame, ledger)`` always produces an
        equal plan. The planner reads ``frame`` and ``ledger`` only;
        neither is mutated.

        ``ledger`` is currently unused for model selection — the
        per-frame token estimate is sufficient for the long-context
        threshold check (Requirement 11.6). The parameter is kept on
        the signature so future refinements (e.g. mission-cumulative
        context-window pressure) can consult the ledger without
        another contract change.
        """

        # 1) Token estimate — same resolution order as TokenBudgetGovernor.
        estimated_tokens = _estimate_frame_tokens(frame)

        # 2) Model selection — long-context override above the threshold.
        if estimated_tokens > LONG_CONTEXT_TOKEN_THRESHOLD:
            model_id = LONG_CONTEXT_MODEL_ID
            rationale_model = _RATIONALE_LONG_CONTEXT
        else:
            model_id = self._default_model_id
            rationale_model = _RATIONALE_DEFAULT

        # 3) Backend selection — derived from model_id prefix.
        backend = self._select_backend(model_id)

        # 4) Runtime selection — streaming flag if exposed by frame or
        #    its underlying model definition.
        runtime = self._select_runtime(frame)

        # 5) Prefix-reuse strategy — Requirement 9.3.
        existing_prefix_hash = getattr(frame, "stable_prefix_hash", None)
        if isinstance(existing_prefix_hash, str) and existing_prefix_hash:
            stable_prefix_hash: str | None = existing_prefix_hash
        else:
            stable_prefix_hash = _compute_stable_prefix_hash(frame)
        use_prefix_reuse = stable_prefix_hash is not None

        # 6) Evidence delta count — len(top_k_evidence) for the first
        #    call; the prompt-frame cache computes the real delta.
        top_k = getattr(frame, "top_k_evidence", None)
        evidence_delta_count = len(top_k) if top_k is not None else 0

        # 7) Rationale — combine model rationale and prefix-reuse note.
        rationale = (
            f"{rationale_model}+{_RATIONALE_PREFIX_REUSE}"
            if use_prefix_reuse
            else rationale_model
        )

        return ModelCallPlan(
            model_id=model_id,
            backend=backend,
            runtime=runtime,
            use_prefix_reuse=use_prefix_reuse,
            stable_prefix_hash=stable_prefix_hash,
            evidence_delta_count=evidence_delta_count,
            estimated_input_tokens=estimated_tokens,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_backend(self, model_id: str) -> str:
        """Resolve backend from ``model_id`` prefix.

        Case-insensitive prefix match: ``gpt-*`` → ``openai``,
        ``claude-*`` → ``anthropic``. Anything else falls back to
        the constructor's ``default_backend``.
        """

        lowered = model_id.lower()
        if lowered.startswith("gpt-"):
            return BACKEND_OPENAI
        if lowered.startswith("claude-"):
            return BACKEND_ANTHROPIC
        return self._default_backend

    @staticmethod
    def _select_runtime(frame: Any) -> str:
        """Resolve runtime from a ``streaming`` flag if exposed.

        Checks ``frame.streaming`` first, then any nested model
        definition reachable as ``frame.user_model.streaming`` or
        ``frame.capability_profile.streaming``. Falls back to
        :data:`RUNTIME_COMPLETION`. ``"batch"`` is reserved for the
        batch-execution planner and is never selected from a
        single-frame plan.
        """

        for path in (
            ("streaming",),
            ("user_model", "streaming"),
            ("capability_profile", "streaming"),
        ):
            target: Any = frame
            for attr in path:
                target = getattr(target, attr, None)
                if target is None:
                    break
            if target:  # truthy → streaming requested
                return RUNTIME_STREAMING
        return RUNTIME_COMPLETION
