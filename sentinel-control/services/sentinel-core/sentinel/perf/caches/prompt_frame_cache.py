"""PromptFrameCache — caches rendered prompt text keyed by ``frame_hash``.

Task 6.2 / sentinel-performance-runtime-foundation.

Requirements: 2.2, 2.6, 9.3.

Scope summary
-------------

This module provides :class:`PromptFrameCache`, an LRU-bounded, in-memory
cache that maps :attr:`LLMDecisionFrame.frame_hash` to a previously
rendered prompt string. The cache exists so the cognitive cycle's
prompt-rendering call sites do not have to re-render an unchanged
:class:`LLMDecisionFrame` on every tick (Requirement 2.2).

A second, independent LRU table (``_prefix_cache``) maps a caller-
supplied ``stable_prefix_hash`` to a previously rendered "stable prefix"
string. :meth:`PromptFrameCache.reuse_prefix` uses that table to satisfy
Requirement 9.3 — append-only evidence deltas can be served by
concatenating the stable prefix with a deterministic rendering of the
delta, which equals the rendered prompt that a full rebuild would
produce.

Equivalence model (Requirement 2.2 / 2.6)
-----------------------------------------

Cached rendered prompt text is compared against a fresh render under
canonical-form equivalence — for rendered prompt strings, that
canonical form is the rendered string itself (string equality). Raw
object-byte comparison is not used; the cache stores the rendered
string returned by ``renderer(frame)``.

When ``get_or_render(..., verify=True)`` is called and the entry is
present, the cache invokes ``renderer(frame)`` to produce a fresh
string and compares the cached and fresh strings:

* on match — emits :data:`AgentEventType.CACHE_HIT` and returns the
  cached string;
* on divergence — emits
  :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` with payload
  ``{cache_type, frame_hash, mismatch_description, mission_id}``
  (no prompt text, no frame body, no evidence content), evicts the
  cached entry, increments ``correctness_violations``, and returns the
  freshly-rendered string. ``renderer`` is invoked exactly once on the
  divergence path — there is no second recompute.

This matches the Property 3 invariant in the spec: a single fresh
render settles the divergence.

Hard-constraint event payload schema (Requirement 12.1 / 12.8)
--------------------------------------------------------------

Events emitted by this cache **never** carry rendered prompt text,
frame bodies, raw user input, evidence card content, raw artifact
blobs, or secrets. Every payload is restricted to the whitelist:

* ``cache_type``           — fixed string ``"prompt"`` or
                             ``"prompt_prefix"``;
* ``frame_hash`` /
  ``prefix_hash``          — the SHA-256 hex hash, not its inputs;
* ``mission_id``           — caller-supplied identifier or ``None``;
* ``mismatch_description`` — short, static, human-readable string,
                             only on the
                             ``CACHE_CORRECTNESS_VIOLATION`` event,
                             never derived from user content.

String immutability
-------------------

Python ``str`` objects are immutable, so the cache stores and returns
the rendered prompt strings directly without defensive copies. A
caller cannot mutate a returned string in a way that affects another
caller's view of the cache.

Authority property (Requirement 12.7)
-------------------------------------

The cache is keyed by :attr:`LLMDecisionFrame.frame_hash`, which is
computed from the frame's mission card, authority card, evidence,
tool surface, and required output schema (see
:func:`sentinel.agent.decision_frame._stable_hash` and
:meth:`LLMDecisionFrame.build`). A frame built under different
authority hashes to a different ``frame_hash`` and is therefore a
different cache entry. Cache reads can never silently broaden the
authority envelope of a downstream prompt — they only return the
rendered text that the *original* renderer produced for the *original*
authority-bearing frame.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.agent.evidence_ranker import EvidenceCard
from sentinel.shared.events import AgentEventType, EventBus

__all__ = [
    "CACHE_TYPE",
    "CACHE_TYPE_PREFIX",
    "DEFAULT_MAX_ENTRIES",
    "PromptFrameCache",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


CACHE_TYPE: str = "prompt"
"""Fixed ``cache_type`` tag used in events for the rendered-prompt table.

Reused as the ``cache_type`` discriminator on
:data:`AgentEventType.CACHE_HIT`, :data:`AgentEventType.CACHE_MISS`,
:data:`AgentEventType.CACHE_EVICTED`, and
:data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` events emitted on the
existing :class:`sentinel.shared.events.EventBus`.
"""

CACHE_TYPE_PREFIX: str = "prompt_prefix"
"""Fixed ``cache_type`` tag used in events for the stable-prefix table."""

DEFAULT_MAX_ENTRIES: int = 256
"""Default LRU capacity for both the frame and prefix tables."""


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------


def _stable_hash(payload: dict[str, Any]) -> str:
    """Canonical SHA-256 hex digest of ``payload``.

    Identical to :func:`sentinel.agent.decision_frame._stable_hash` and
    :func:`sentinel.perf.caches.context_build_cache._stable_hash` so any
    hash this module produces is interchangeable with hashes elsewhere
    in the cognitive layer (sorted keys, no whitespace, ASCII escapes).

    The helper is duplicated privately rather than imported to keep
    :mod:`sentinel.perf.caches.prompt_frame_cache` self-contained — the
    cache module owns its hashing surface and does not pull in the
    decision-frame module's private helpers.
    """

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Evidence-delta rendering (Requirement 9.3)
# ---------------------------------------------------------------------------


def _render_evidence_delta(evidence_delta: list[EvidenceCard]) -> str:
    """Render an append-only evidence delta deterministically.

    Each :class:`EvidenceCard` is emitted as a single line of the form::

        - {summary} (receipt={receipt_id})\n

    The rendering preserves the order of ``evidence_delta`` — the
    caller controls ordering — and contains no fields beyond the
    sanitised ``summary`` and ``receipt_id``. ``EvidenceCard.summary``
    is already passed through
    :func:`sentinel.agent.evidence_ranker.sanitize_context_text` at
    construction time (see ``EvidenceRanker._card``), so no additional
    sanitisation is performed here.

    The rendering is deterministic — equal inputs produce equal output
    — which is what
    :meth:`PromptFrameCache.reuse_prefix` needs to guarantee that
    ``prefix_text + _render_evidence_delta(delta)`` equals the rendered
    prompt a full rebuild would produce for the same delta.
    """

    if not evidence_delta:
        return ""
    return "".join(
        f"- {card.summary} (receipt={card.receipt_id})\n" for card in evidence_delta
    )


# ---------------------------------------------------------------------------
# PromptFrameCache
# ---------------------------------------------------------------------------


class PromptFrameCache:
    """Caches rendered prompt text keyed by :attr:`LLMDecisionFrame.frame_hash`.

    Requirements: 2.2, 2.6, 9.3.

    Storage discipline
    ------------------

    * The frame table (``_entries``) maps ``frame_hash`` to the rendered
      prompt string. Entries are managed as a strict LRU: every read
      promotes the entry to the tail; on insert, the head is evicted
      while ``len > max_entries``. ``str`` is immutable, so no
      defensive copies are required.
    * The prefix table (``_prefix_cache``) maps a caller-supplied
      ``stable_prefix_hash`` to a previously rendered prefix string.
      The same LRU discipline applies and the same capacity bound is
      enforced.

    Event discipline
    ----------------

    Every cache event payload is restricted to
    ``{cache_type, frame_hash, mission_id}`` for the frame table or
    ``{cache_type, prefix_hash, mission_id}`` for the prefix table,
    plus ``mismatch_description`` on the violation event. No rendered
    prompt text, frame body, evidence content, raw user input, or
    secrets ever appear in an event payload. See module docstring for
    the hard-constraint statement.
    """

    def __init__(self, *, event_bus: EventBus, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("PromptFrameCache.max_entries must be >= 1")
        self._event_bus = event_bus
        self._max_entries = max_entries
        self._entries: OrderedDict[str, str] = OrderedDict()
        self._prefix_cache: OrderedDict[str, str] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._correctness_violations = 0

    # ------------------------------------------------------------------
    # Public API — frame-keyed rendering
    # ------------------------------------------------------------------

    def get_or_render(
        self,
        frame: LLMDecisionFrame,
        renderer: Callable[[LLMDecisionFrame], str],
        *,
        verify: bool = False,
        mission_id: str | None = None,
    ) -> str:
        """Return a cached or freshly rendered prompt string.

        * ``verify=False`` (production mode, Requirement 2.2): on cache
          hit emit :data:`AgentEventType.CACHE_HIT`, increment the hit
          counter, promote the entry to the LRU tail, and return the
          cached string. On cache miss emit
          :data:`AgentEventType.CACHE_MISS`, invoke ``renderer(frame)``,
          store the rendered string, evict the oldest entry if capacity
          is exceeded (each eviction emits
          :data:`AgentEventType.CACHE_EVICTED`), and return the fresh
          rendered string.
        * ``verify=True`` (diagnostic mode, Requirement 2.6): on cache
          hit invoke ``renderer(frame)`` and compare the cached string
          to the fresh string. On match, emit
          :data:`AgentEventType.CACHE_HIT` and return the cached
          string. On divergence, emit
          :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION`, evict the
          entry, increment ``correctness_violations``, and return the
          freshly rendered string (no second recompute). On cache miss,
          fall through to the ``verify=False`` miss path; ``renderer``
          is invoked exactly once.

        ``mission_id`` is purely descriptive — it is forwarded into the
        event payload so downstream observers can correlate cache
        events with mission timelines without touching the prompt
        body.
        """

        key = frame.frame_hash
        if key in self._entries:
            cached = self._entries[key]
            self._entries.move_to_end(key)
            if verify:
                fresh = renderer(frame)
                if cached == fresh:
                    self._hits += 1
                    self._emit_hit(key=key, mission_id=mission_id)
                    return cached
                # Divergence — evict, return fresh, do not recompute.
                self._correctness_violations += 1
                del self._entries[key]
                self._emit_correctness_violation(
                    key=key,
                    mission_id=mission_id,
                    mismatch_description=(
                        "prompt_frame_cache canonical-form divergence between "
                        "cached rendered prompt and fresh renderer(frame) output"
                    ),
                )
                return fresh
            self._hits += 1
            self._emit_hit(key=key, mission_id=mission_id)
            return cached

        # Cache miss
        self._misses += 1
        self._emit_miss(key=key, mission_id=mission_id)
        fresh = renderer(frame)
        self._entries[key] = fresh
        self._enforce_capacity()
        return fresh

    def invalidate(self, frame_hash: str) -> bool:
        """Remove ``frame_hash`` from the rendered-prompt table.

        Returns ``True`` if the entry existed and was removed (and a
        :data:`AgentEventType.CACHE_EVICTED` event was emitted),
        ``False`` if the key was not present (no event emitted).
        """

        if frame_hash not in self._entries:
            return False
        del self._entries[frame_hash]
        self._evictions += 1
        self._emit_evicted(key=frame_hash, mission_id=None)
        return True

    # ------------------------------------------------------------------
    # Public API — stable-prefix reuse (Requirement 9.3)
    # ------------------------------------------------------------------

    def register_prefix(self, stable_prefix_hash: str, prefix_text: str) -> None:
        """Store a stable prefix string under ``stable_prefix_hash``.

        Called by the caller after a full prompt rebuild to populate
        the prefix table. The prefix text is what
        :meth:`reuse_prefix` will concatenate with the rendered evidence
        delta for subsequent append-only delta requests.

        The prefix table follows the same LRU capacity bound as the
        frame table. ``str`` is immutable, so the prefix is stored as
        the same object passed in.
        """

        if stable_prefix_hash in self._prefix_cache:
            # Promote and overwrite.
            self._prefix_cache.move_to_end(stable_prefix_hash)
        self._prefix_cache[stable_prefix_hash] = prefix_text
        self._enforce_prefix_capacity()

    def reuse_prefix(
        self,
        stable_prefix_hash: str,
        evidence_delta: list[EvidenceCard],
        *,
        mission_id: str | None = None,
    ) -> str | None:
        """Append-only delta reuse. Requirement 9.3.

        If ``stable_prefix_hash`` is registered in the prefix table:
        emit :data:`AgentEventType.CACHE_HIT` with payload
        ``{cache_type: "prompt_prefix", prefix_hash, mission_id}``,
        promote the prefix to the LRU tail, and return
        ``prefix + _render_evidence_delta(evidence_delta)``. The output
        equals the rendered prompt that a full rebuild would produce
        for the same delta — the prefix is byte-stable and the delta
        is appended (not interleaved).

        If ``stable_prefix_hash`` is not registered: emit
        :data:`AgentEventType.CACHE_MISS` with the same payload shape
        and return ``None``. The caller is expected to perform a full
        rebuild and may then call :meth:`register_prefix` to populate
        the prefix table for future reuse.
        """

        if stable_prefix_hash in self._prefix_cache:
            prefix = self._prefix_cache[stable_prefix_hash]
            self._prefix_cache.move_to_end(stable_prefix_hash)
            self._hits += 1
            self._emit_prefix_hit(prefix_hash=stable_prefix_hash, mission_id=mission_id)
            return prefix + _render_evidence_delta(evidence_delta)

        self._misses += 1
        self._emit_prefix_miss(prefix_hash=stable_prefix_hash, mission_id=mission_id)
        return None

    # ------------------------------------------------------------------
    # Public API — observability
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Return current cache counters and combined size.

        Keys: ``hits``, ``misses``, ``evictions``,
        ``correctness_violations``, ``size``. ``size`` reports the sum
        of the frame and prefix tables — both contribute to the
        cache's memory footprint.
        """

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "correctness_violations": self._correctness_violations,
            "size": len(self._entries) + len(self._prefix_cache),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """LRU eviction for the frame table: drop oldest until in bounds."""

        while len(self._entries) > self._max_entries:
            evicted_key, _ = self._entries.popitem(last=False)
            self._evictions += 1
            self._emit_evicted(key=evicted_key, mission_id=None)

    def _enforce_prefix_capacity(self) -> None:
        """LRU eviction for the prefix table: drop oldest until in bounds."""

        while len(self._prefix_cache) > self._max_entries:
            evicted_key, _ = self._prefix_cache.popitem(last=False)
            self._evictions += 1
            self._emit_prefix_evicted(prefix_hash=evicted_key, mission_id=None)

    def _emit_hit(self, *, key: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_HIT,
            "prompt_frame_cache hit",
            payload={
                "cache_type": CACHE_TYPE,
                "frame_hash": key,
                "mission_id": mission_id,
            },
        )

    def _emit_miss(self, *, key: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_MISS,
            "prompt_frame_cache miss",
            payload={
                "cache_type": CACHE_TYPE,
                "frame_hash": key,
                "mission_id": mission_id,
            },
        )

    def _emit_evicted(self, *, key: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_EVICTED,
            "prompt_frame_cache evicted",
            payload={
                "cache_type": CACHE_TYPE,
                "frame_hash": key,
                "mission_id": mission_id,
            },
        )

    def _emit_correctness_violation(
        self,
        *,
        key: str,
        mission_id: str | None,
        mismatch_description: str,
    ) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_CORRECTNESS_VIOLATION,
            "prompt_frame_cache canonical-form divergence",
            payload={
                "cache_type": CACHE_TYPE,
                "frame_hash": key,
                "mismatch_description": mismatch_description,
                "mission_id": mission_id,
            },
        )

    def _emit_prefix_hit(self, *, prefix_hash: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_HIT,
            "prompt_frame_cache prefix hit",
            payload={
                "cache_type": CACHE_TYPE_PREFIX,
                "prefix_hash": prefix_hash,
                "mission_id": mission_id,
            },
        )

    def _emit_prefix_miss(self, *, prefix_hash: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_MISS,
            "prompt_frame_cache prefix miss",
            payload={
                "cache_type": CACHE_TYPE_PREFIX,
                "prefix_hash": prefix_hash,
                "mission_id": mission_id,
            },
        )

    def _emit_prefix_evicted(self, *, prefix_hash: str, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_EVICTED,
            "prompt_frame_cache prefix evicted",
            payload={
                "cache_type": CACHE_TYPE_PREFIX,
                "prefix_hash": prefix_hash,
                "mission_id": mission_id,
            },
        )
