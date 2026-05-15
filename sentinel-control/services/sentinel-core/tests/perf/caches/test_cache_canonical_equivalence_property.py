# Feature: sentinel-performance-runtime-foundation, Property 3: Cache canonical-form equivalence and correctness fallback
"""Property test — cache canonical-form equivalence and runtime fallback.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6.**

Property statement
------------------

Hypothesis-generated composite-key-equivalent pairs across all three
caches in the cognitive layer (:class:`ContextBuildCache`,
:class:`PromptFrameCache`, :class:`LLMDecisionFrameCache`). Under
``verify=True`` every divergence between a cached result and a fresh
recomputation:

* evicts the cached entry,
* emits :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` whose
  payload carries
  ``(cache_type, composite_key | frame_hash, mismatch_description, mission_id)``
  and nothing else,
* returns the freshly recomputed value, and
* invokes the builder/renderer exactly once on the divergence path
  (no second recompute).

Across every violation path the emitted payload never contains raw
context bodies, prompt bodies, evidence summaries, or any
user-supplied substrings.

Hypothesis settings
-------------------

``max_examples=100, deadline=None`` per the task spec.
``HealthCheck.too_slow`` is suppressed because per-example cache
construction and event-stream walking are slightly slower than the
default Hypothesis budget; total runtime per test is small.
"""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.agent.models import AgentContext
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.caches.context_build_cache import (
    CACHE_TYPE as CONTEXT_CACHE_TYPE,
)
from sentinel.perf.caches.context_build_cache import ContextBuildCache
from sentinel.perf.caches.llm_decision_frame_cache import (
    CACHE_TYPE as FRAME_CACHE_TYPE,
)
from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache
from sentinel.perf.caches.prompt_frame_cache import (
    CACHE_TYPE as PROMPT_CACHE_TYPE,
)
from sentinel.perf.caches.prompt_frame_cache import (
    CACHE_TYPE_PREFIX as PROMPT_PREFIX_CACHE_TYPE,
)
from sentinel.perf.caches.prompt_frame_cache import PromptFrameCache
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.shared.events import AgentEvent, AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p3"

# Whitelist of permitted payload keys per cache_type per event family.
# Mirrors the documented contracts in the cache module docstrings; if
# any cache adds a new key it must be added here too — that is the
# point of the assertion.
_CTX_KEYS_BASE = {"cache_type", "composite_key", "mission_id"}
_PROMPT_FRAME_KEYS_BASE = {"cache_type", "frame_hash", "mission_id"}
_PROMPT_PREFIX_KEYS_BASE = {"cache_type", "prefix_hash", "mission_id"}
_FRAME_KEYS_BASE = {"cache_type", "composite", "mission_id"}


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# User-content strings used for AgentContext bodies, prompt bodies, and
# user_input values. The alphabet is restricted to lowercase ASCII +
# digits and the strategy maps every example through a ``USER_`` prefix
# so:
#   1. Generated values cannot trigger the canonical secret-redaction
#      patterns (sk-/sk_, etc.) used by ``sanitize_context_text``.
#   2. The ``USER_`` prefix contains an underscore (``_``), which never
#      appears in a SHA-256 hex digest. That makes accidental substring
#      collision with ``composite_key`` / ``frame_hash`` (both hex)
#      structurally impossible — the substring assertion in
#      ``test_event_payloads_never_contain_bodies`` therefore can only
#      fire on a real leak.
_USER_CONTENT = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=12,
    max_size=32,
).map(lambda s: f"USER_{s}")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _envelope() -> MissionAuthorityEnvelope:
    """Minimal :class:`MissionAuthorityEnvelope` for cache testing.

    The envelope's ``created_at`` differs between calls (default factory
    is :func:`utc_now`). That is intentional: it exercises the
    canonical-form ``*_at`` stripping rule
    (:func:`_strip_volatile_at_fields`) — two envelopes built in the
    same test step have different timestamps but produce identical
    canonical forms.
    """
    return MissionAuthorityEnvelope(
        user_id="user_test",
        mission_type=MissionType.GTM,
        mission_title="Cache canonical equivalence test",
        mission_objective="Validate Property 3 invariants.",
        success_criteria=["test"],
        mode=MissionMode.SAFE,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_tool"],
        allowed_actions=["read_action"],
        max_duration_minutes=10,
        max_actions=5,
    )


def _context(
    *,
    summary: str = "",
    constraints: list[str] | None = None,
    user_input: dict[str, Any] | None = None,
) -> AgentContext:
    """Build a small :class:`AgentContext` with a fresh envelope per call."""
    return AgentContext(
        mission=_envelope(),
        user_input=user_input or {},
        evidence_refs=[],
        memory_items=[],
        constraints=list(constraints) if constraints else [],
        available_capabilities=[],
        available_tools=[],
        world_model_refs=[],
        summary=summary,
    )


def _composite_key(cache: ContextBuildCache) -> str:
    """Stable composite key shared by every test in this module."""
    return cache.composite_key(
        mission_hot_hash="hot_hash_v1",
        workspace_snapshot_id="ws_snapshot_v1",
        organ_state_hash="organ_state_v1",
        authority_hash="auth_hash_v1",
    )


def _frame(frame_hash: str = "frame_hash_v1") -> SimpleNamespace:
    """Minimal frame-shaped object for :class:`PromptFrameCache`.

    :meth:`PromptFrameCache.get_or_render` only reads ``frame.frame_hash``;
    a :class:`types.SimpleNamespace` is sufficient and avoids the
    heavyweight :meth:`LLMDecisionFrame.build` pipeline that would
    require a full ``UserModelContract``, ranked evidence, and a
    budget allocator just to populate one attribute.
    """
    return SimpleNamespace(frame_hash=frame_hash)


# ---------------------------------------------------------------------------
# Counter mock
# ---------------------------------------------------------------------------


class _CallCounter:
    """Wrap a callable, count invocations.

    Used in place of a builder/renderer so the ``no second recompute``
    invariant on the divergence path can be asserted directly.
    """

    def __init__(self, fn: Callable[..., Any]) -> None:
        self._fn = fn
        self.calls = 0

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        return self._fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Payload-whitelist helper
# ---------------------------------------------------------------------------


def _expected_payload_keys(event: AgentEvent) -> set[str]:
    """Return the whitelist of permitted payload keys for ``event``.

    The whitelist depends on (cache_type, event_type):

    * ContextBuildCache (``cache_type == "context"``) —
      hit/miss/evicted carry ``{cache_type, composite_key, mission_id}``;
      :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` adds
      ``mismatch_description``.
    * PromptFrameCache frame-table (``cache_type == "prompt"``) —
      hit/miss/evicted carry ``{cache_type, frame_hash, mission_id}``;
      :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` adds
      ``mismatch_description``.
    * PromptFrameCache prefix-table (``cache_type == "prompt_prefix"``)
      — hit/miss/evicted carry
      ``{cache_type, prefix_hash, mission_id}``.
    * LLMDecisionFrameCache (``cache_type == "frame"``) —
      hit/miss carry ``{cache_type, composite, mission_id}``;
      :data:`AgentEventType.CACHE_EVICTED` adds ``reason``.

    Any payload key outside this whitelist is, by construction, not
    documented in the module's hard-constraint event-payload schema
    and would constitute a body-leak surface.
    """
    cache_type = event.payload.get("cache_type")
    if cache_type == CONTEXT_CACHE_TYPE:
        if event.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION:
            return _CTX_KEYS_BASE | {"mismatch_description"}
        return _CTX_KEYS_BASE
    if cache_type == PROMPT_CACHE_TYPE:
        if event.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION:
            return _PROMPT_FRAME_KEYS_BASE | {"mismatch_description"}
        return _PROMPT_FRAME_KEYS_BASE
    if cache_type == PROMPT_PREFIX_CACHE_TYPE:
        return _PROMPT_PREFIX_KEYS_BASE
    if cache_type == FRAME_CACHE_TYPE:
        if event.event_type == AgentEventType.CACHE_EVICTED:
            return _FRAME_KEYS_BASE | {"reason"}
        return _FRAME_KEYS_BASE
    # Unknown cache_type — surfaces as an empty whitelist so the
    # caller's set-subset assertion fails loudly.
    return set()


# ---------------------------------------------------------------------------
# 1. ContextBuildCache — verify=True with matching builder returns cached
# ---------------------------------------------------------------------------


@given(summary=_USER_CONTENT, constraint=_USER_CONTENT)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_context_cache_verify_match_returns_cached(
    summary: str, constraint: str
) -> None:
    """verify=True with matching builder → CACHE_HIT, no violation.

    First build (verify=False) populates the cache. Second build
    (verify=True) uses a closure that returns the same context. The
    canonical-form comparison matches; :data:`AgentEventType.CACHE_HIT`
    is emitted; no :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION`
    appears anywhere in the event stream.

    Validates: Requirements 2.1, 2.4.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    cache = ContextBuildCache(event_bus=bus)
    key = _composite_key(cache)

    ctx = _context(summary=summary, constraints=[constraint])

    # Populate cache.
    first = cache.get_or_build(key, lambda: ctx, mission_id=_MISSION_ID)
    assert first.summary == summary

    # verify=True with a builder that always returns the same context.
    counter = _CallCounter(lambda: ctx)
    result = cache.get_or_build(
        key, counter, verify=True, mission_id=_MISSION_ID
    )

    assert result.summary == summary
    assert result.constraints == [constraint]

    # Builder invoked exactly once on the verify=True hit path
    # (called for the canonical-form comparison, not stored).
    assert counter.calls == 1

    # Last cache event is CACHE_HIT.
    cache_events = [
        ev
        for ev in bus.events()
        if ev.event_type
        in (
            AgentEventType.CACHE_HIT,
            AgentEventType.CACHE_MISS,
            AgentEventType.CACHE_EVICTED,
            AgentEventType.CACHE_CORRECTNESS_VIOLATION,
        )
    ]
    assert cache_events[-1].event_type == AgentEventType.CACHE_HIT

    # No violation anywhere.
    violations = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION
    ]
    assert violations == []


# ---------------------------------------------------------------------------
# 2. ContextBuildCache — verify=True with divergent builder evicts + fresh
# ---------------------------------------------------------------------------


@given(summary_a=_USER_CONTENT, summary_b=_USER_CONTENT)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_context_cache_verify_divergence_evicts_and_returns_fresh(
    summary_a: str, summary_b: str
) -> None:
    """verify=True divergence path evicts, emits violation, returns fresh.

    First build populates with ``ctx_a``. Second build with
    ``verify=True`` uses a builder that returns ``ctx_b`` whose
    summary differs. The canonical-form comparison fails;
    :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` is emitted with
    payload keys ``{cache_type, composite_key, mismatch_description,
    mission_id}``; the cached entry is evicted; the fresh ``ctx_b``
    is returned; the builder is invoked exactly once.

    Validates: Requirements 2.1, 2.4, 2.5, 2.6.
    """
    # Hypothesis can sample equal pairs; force divergence so the test
    # actually exercises the divergence path.
    if summary_a == summary_b:
        summary_b = summary_b + "_x"

    bus = EventBus(mission_id=_MISSION_ID)
    cache = ContextBuildCache(event_bus=bus)
    key = _composite_key(cache)

    ctx_a = _context(summary=summary_a)
    ctx_b = _context(summary=summary_b)

    cache.get_or_build(key, lambda: ctx_a, mission_id=_MISSION_ID)

    counter = _CallCounter(lambda: ctx_b)
    result = cache.get_or_build(
        key, counter, verify=True, mission_id=_MISSION_ID
    )

    # Returned value is the fresh build.
    assert result.summary == summary_b

    # Builder invoked exactly once on the divergence path
    # (no second recompute).
    assert counter.calls == 1, (
        f"divergence path must invoke builder exactly once, got {counter.calls}"
    )

    # Exactly one CACHE_CORRECTNESS_VIOLATION emitted with the
    # whitelisted payload shape.
    violations = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION
    ]
    assert len(violations) == 1
    payload = violations[0].payload
    assert set(payload.keys()) == {
        "cache_type",
        "composite_key",
        "mismatch_description",
        "mission_id",
    }
    assert payload["cache_type"] == CONTEXT_CACHE_TYPE
    assert payload["composite_key"] == key
    assert payload["mission_id"] == _MISSION_ID
    assert isinstance(payload["mismatch_description"], str)
    assert payload["mismatch_description"]  # non-empty

    # Cached entry was evicted: subsequent get is a miss
    # (re-invokes its builder).
    miss_counter = _CallCounter(lambda: ctx_b)
    cache.get_or_build(key, miss_counter, mission_id=_MISSION_ID)
    assert miss_counter.calls == 1, (
        "post-divergence get must be a miss — the entry should have "
        "been evicted, but the builder was not invoked"
    )


# ---------------------------------------------------------------------------
# 3. PromptFrameCache — verify=True with matching renderer returns cached
# ---------------------------------------------------------------------------


@given(prompt=_USER_CONTENT)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_prompt_cache_verify_match_returns_cached(prompt: str) -> None:
    """verify=True with matching renderer → CACHE_HIT, no violation.

    Validates: Requirements 2.2, 2.4.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    cache = PromptFrameCache(event_bus=bus)
    frame = _frame()

    first = cache.get_or_render(
        frame, lambda f: prompt, mission_id=_MISSION_ID
    )
    assert first == prompt

    counter = _CallCounter(lambda f: prompt)
    result = cache.get_or_render(
        frame, counter, verify=True, mission_id=_MISSION_ID
    )

    assert result == prompt
    assert counter.calls == 1

    cache_events = [
        ev
        for ev in bus.events()
        if ev.event_type
        in (
            AgentEventType.CACHE_HIT,
            AgentEventType.CACHE_MISS,
            AgentEventType.CACHE_EVICTED,
            AgentEventType.CACHE_CORRECTNESS_VIOLATION,
        )
    ]
    assert cache_events[-1].event_type == AgentEventType.CACHE_HIT

    violations = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION
    ]
    assert violations == []


# ---------------------------------------------------------------------------
# 4. PromptFrameCache — verify=True with divergent renderer evicts + fresh
# ---------------------------------------------------------------------------


@given(prompt_a=_USER_CONTENT, prompt_b=_USER_CONTENT)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_prompt_cache_verify_divergence_evicts_and_returns_fresh(
    prompt_a: str, prompt_b: str
) -> None:
    """verify=True divergence path evicts, emits violation, returns fresh.

    Validates: Requirements 2.2, 2.4, 2.5, 2.6.
    """
    if prompt_a == prompt_b:
        prompt_b = prompt_b + "_x"

    bus = EventBus(mission_id=_MISSION_ID)
    cache = PromptFrameCache(event_bus=bus)
    frame = _frame()

    cache.get_or_render(
        frame, lambda f: prompt_a, mission_id=_MISSION_ID
    )

    counter = _CallCounter(lambda f: prompt_b)
    result = cache.get_or_render(
        frame, counter, verify=True, mission_id=_MISSION_ID
    )

    assert result == prompt_b
    assert counter.calls == 1

    violations = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION
    ]
    assert len(violations) == 1
    payload = violations[0].payload
    assert set(payload.keys()) == {
        "cache_type",
        "frame_hash",
        "mismatch_description",
        "mission_id",
    }
    assert payload["cache_type"] == PROMPT_CACHE_TYPE
    assert payload["frame_hash"] == frame.frame_hash
    assert payload["mission_id"] == _MISSION_ID
    assert isinstance(payload["mismatch_description"], str)
    assert payload["mismatch_description"]

    # Cached entry was evicted: subsequent get is a miss.
    miss_counter = _CallCounter(lambda f: prompt_b)
    cache.get_or_render(frame, miss_counter, mission_id=_MISSION_ID)
    assert miss_counter.calls == 1, (
        "post-divergence get must be a miss — the entry should have "
        "been evicted, but the renderer was not invoked"
    )


# ---------------------------------------------------------------------------
# 5. No second recompute on divergence (both caches)
# ---------------------------------------------------------------------------


@given(
    summary_a=_USER_CONTENT,
    summary_b=_USER_CONTENT,
    prompt_a=_USER_CONTENT,
    prompt_b=_USER_CONTENT,
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_no_second_recompute_on_divergence(
    summary_a: str,
    summary_b: str,
    prompt_a: str,
    prompt_b: str,
) -> None:
    """Both caches invoke the builder/renderer exactly once on divergence.

    Property 3 invariant: a single fresh recomputation settles the
    divergence — there is no second pass.

    Validates: Requirements 2.5.
    """
    if summary_a == summary_b:
        summary_b = summary_b + "_x"
    if prompt_a == prompt_b:
        prompt_b = prompt_b + "_x"

    # ContextBuildCache divergence path.
    ctx_bus = EventBus(mission_id=_MISSION_ID)
    ctx_cache = ContextBuildCache(event_bus=ctx_bus)
    ctx_key = _composite_key(ctx_cache)
    ctx_cache.get_or_build(
        ctx_key,
        lambda: _context(summary=summary_a),
        mission_id=_MISSION_ID,
    )
    ctx_counter = _CallCounter(lambda: _context(summary=summary_b))
    ctx_cache.get_or_build(
        ctx_key, ctx_counter, verify=True, mission_id=_MISSION_ID
    )
    assert ctx_counter.calls == 1, (
        "ContextBuildCache divergence path must invoke builder "
        f"exactly once, got {ctx_counter.calls}"
    )

    # PromptFrameCache divergence path.
    p_bus = EventBus(mission_id=_MISSION_ID)
    p_cache = PromptFrameCache(event_bus=p_bus)
    frame = _frame()
    p_cache.get_or_render(
        frame, lambda f: prompt_a, mission_id=_MISSION_ID
    )
    p_counter = _CallCounter(lambda f: prompt_b)
    p_cache.get_or_render(
        frame, p_counter, verify=True, mission_id=_MISSION_ID
    )
    assert p_counter.calls == 1, (
        "PromptFrameCache divergence path must invoke renderer "
        f"exactly once, got {p_counter.calls}"
    )


# ---------------------------------------------------------------------------
# 6. Event payloads never contain bodies / user-supplied substrings
# ---------------------------------------------------------------------------


@given(
    summary=_USER_CONTENT,
    summary_b=_USER_CONTENT,
    constraint=_USER_CONTENT,
    user_value=_USER_CONTENT,
    prompt_a=_USER_CONTENT,
    prompt_b=_USER_CONTENT,
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_event_payloads_never_contain_bodies(
    summary: str,
    summary_b: str,
    constraint: str,
    user_value: str,
    prompt_a: str,
    prompt_b: str,
) -> None:
    """No event payload contains raw context bodies, prompt bodies,
    evidence summaries, or any user-supplied substring across every
    cache event family — including the
    :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` violation paths
    of both ContextBuildCache and PromptFrameCache.

    The user content is also embedded in the AgentContext (summary,
    constraints, user_input) and the rendered prompt strings, so any
    accidental inclusion of those bodies in the emitted payloads
    would surface here. The ``USER_`` prefix on every generated value
    structurally rules out collision with the hex composite key /
    frame hash.

    Validates: Requirements 2.5, 2.6.
    """
    if summary == summary_b:
        summary_b = summary_b + "_x"
    if prompt_a == prompt_b:
        prompt_b = prompt_b + "_x"

    user_substrings = {
        summary,
        summary_b,
        constraint,
        user_value,
        prompt_a,
        prompt_b,
    }

    bus = EventBus(mission_id=_MISSION_ID)

    # 1. ContextBuildCache: miss → hit-with-verify-divergence path.
    ctx_cache = ContextBuildCache(event_bus=bus)
    ctx_key = _composite_key(ctx_cache)
    ctx_a = _context(
        summary=summary,
        constraints=[constraint],
        user_input={"key": user_value},
    )
    ctx_b = _context(
        summary=summary_b,
        constraints=[constraint],
        user_input={"key": user_value},
    )
    ctx_cache.get_or_build(ctx_key, lambda: ctx_a, mission_id=_MISSION_ID)
    ctx_cache.get_or_build(
        ctx_key, lambda: ctx_b, verify=True, mission_id=_MISSION_ID
    )

    # 2. PromptFrameCache: miss → hit-with-verify-divergence path.
    p_cache = PromptFrameCache(event_bus=bus)
    frame = _frame()
    p_cache.get_or_render(
        frame, lambda f: prompt_a, mission_id=_MISSION_ID
    )
    p_cache.get_or_render(
        frame, lambda f: prompt_b, verify=True, mission_id=_MISSION_ID
    )

    # 3. LLMDecisionFrameCache: miss → put → hit. Exercises the third
    #    cache's event family so the whitelist enforcement covers all
    #    three caches in the cognitive layer (Property 3 scope).
    f_cache = LLMDecisionFrameCache(event_bus=bus)
    f_composite = f_cache.composite_hash(
        mission_hot_hash="hot_hash_v1",
        authority_hash="auth_hash_v1",
        evidence_set_hash="ev_set_v1",
        tool_surface_hash="tool_surface_v1",
    )
    f_cache.get(f_composite, mission_id=_MISSION_ID)  # miss
    f_cache.put(
        f_composite,
        SimpleNamespace(
            frame_hash="frame_hash_v1",
            authority_expansion=False,
            raw_secret_leakage=False,
        ),
        mission_id=_MISSION_ID,
    )
    f_cache.get(f_composite, mission_id=_MISSION_ID)  # hit

    # Walk every event emitted by any cache and assert two invariants:
    #
    #   (a) payload key set is within the cache's documented whitelist
    #       — any new key would be a body-leak surface.
    #   (b) no payload value, stringified, contains any user substring
    #       — every leaked summary/prompt/constraint/user_input would
    #       appear here.
    cache_event_types = {
        AgentEventType.CACHE_HIT,
        AgentEventType.CACHE_MISS,
        AgentEventType.CACHE_EVICTED,
        AgentEventType.CACHE_CORRECTNESS_VIOLATION,
    }
    saw_violation = False
    for ev in bus.events():
        if ev.event_type not in cache_event_types:
            continue
        allowed = _expected_payload_keys(ev)
        assert set(ev.payload.keys()) <= allowed, (
            f"event {ev.event_type} has payload keys "
            f"{set(ev.payload.keys())} not within whitelist {allowed}"
        )
        for value in ev.payload.values():
            if value is None:
                continue
            value_str = str(value)
            for substring in user_substrings:
                assert substring not in value_str, (
                    f"event {ev.event_type} payload field carrying "
                    f"value {value_str!r} contains user substring "
                    f"{substring!r}"
                )
        if ev.event_type == AgentEventType.CACHE_CORRECTNESS_VIOLATION:
            saw_violation = True
            # The violation event carries exactly the documented keys.
            cache_type = ev.payload["cache_type"]
            if cache_type == CONTEXT_CACHE_TYPE:
                assert set(ev.payload.keys()) == (
                    _CTX_KEYS_BASE | {"mismatch_description"}
                )
            elif cache_type == PROMPT_CACHE_TYPE:
                assert set(ev.payload.keys()) == (
                    _PROMPT_FRAME_KEYS_BASE | {"mismatch_description"}
                )

    # Both divergence paths should have produced a violation event.
    assert saw_violation, (
        "expected at least one CACHE_CORRECTNESS_VIOLATION event "
        "from the ContextBuildCache and PromptFrameCache divergence "
        "paths exercised in this test"
    )
