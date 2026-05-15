"""LLMDecisionFrameCache — per-mission cache for ``LLMDecisionFrame`` instances.

Task 6.3 / sentinel-performance-runtime-foundation.

Requirements: 2.3, 2.6, 9.1, 9.2, 9.4, 9.5, 9.6, 9.7, 12.2, 12.3.

Scope summary
-------------

This module provides :class:`LLMDecisionFrameCache`, a per-mission,
LRU-bounded, TTL-bounded cache that maps the composite hash of
``(mission_hot_hash, authority_hash, evidence_set_hash, tool_surface_hash)``
to a previously built :class:`sentinel.agent.decision_frame.LLMDecisionFrame`.

The cache exists so the cognitive cycle can skip the full
``ContextBuilder``/``LLMDecisionFrame.build`` pipeline and proceed directly
to model invocation when a frame has already been built for the same
mission slice (Requirement 9.5). On a composite-hash miss, the caller
is expected to fall through to a full rebuild (Requirement 9.6) and
then ``put`` the result.

Storage layout
--------------

* ``self._entries`` is an outer ``dict[mission_id, OrderedDict[composite_hash, (frame, created_at_ns)]]``.
  The LRU cap (:data:`MAX_ENTRIES_PER_MISSION` = 128) is enforced
  **per mission**, not globally, per Requirement 9.2 ("at most 128
  entries per mission, evicting the least-recently-used entry when
  the limit is reached"). Mission ``A`` filling its cache cannot
  evict any entries belonging to mission ``B``.

* ``self._stats`` is an outer ``dict[mission_id, dict[counter_name, int]]``.
  Per-mission counters (Requirement 9.4) and reported by
  :meth:`stats` for surfacing in mission-level ``PerformanceReceipt``
  aggregates:

  - ``hits``           — incremented only on actual cache hits.
  - ``misses``         — incremented only on actual cache misses
                         (composite-hash miss).
  - ``evictions``      — incremented only on LRU evictions caused by
                         exceeding :data:`MAX_ENTRIES_PER_MISSION`.
  - ``ttl_evictions``  — incremented only on evictions caused by
                         :data:`TTL_SECONDS` expiry on read
                         (Requirement 9.7).
  - ``safety_bypasses``— incremented only on evictions caused by a
                         safety-bypass on read
                         (``authority_expansion=True`` per
                         Requirement 12.2; ``raw_secret_leakage=True``
                         per Requirement 12.3). Stored in the same
                         counter because both have identical operational
                         meaning: "the cached frame is unsafe to serve
                         and was discarded without delivery".

Each counter is incremented exactly when the corresponding event is
emitted; no counter is ever incremented on an outcome that does not
match its event type (Requirement 9.4 ground-truth wording).

Safety contract (Requirement 12.2 / 12.3)
-----------------------------------------

* :meth:`put` rejects ``frame.authority_expansion=True`` with a
  ``ValueError`` (Requirement 12.2). The frame is never stored in
  any form — there is no temporary entry, no half-written record,
  and no event payload that would carry the rejected frame body.

* :meth:`get` rejects (and evicts) any cached entry whose
  ``authority_expansion`` is ``True`` (Requirement 12.2) or whose
  ``raw_secret_leakage`` is ``True`` (Requirement 12.3). The cache
  returns ``None`` (a cache miss from the caller's perspective),
  emits :data:`AgentEventType.CACHE_EVICTED` with a reason tag, and
  increments ``safety_bypasses``. This protects against the case
  where a frame is stored in a clean state but its safety flags are
  later mutated (``LLMDecisionFrame`` inherits the unfrozen
  :class:`sentinel.shared.models.SentinelModel`, so post-construction
  mutation is structurally possible).

Event payload schema (Requirement 12.1 / 12.8)
----------------------------------------------

Events emitted by this cache **never** carry frame bodies, evidence
card content, prompt text, raw user input, secret values, or
artifact bytes. Every payload is restricted to the whitelist:

* ``cache_type``  — fixed string ``"frame"``;
* ``composite``   — the SHA-256 hex composite hash, not its inputs;
* ``mission_id``  — the caller-supplied mission identifier;
* ``reason``      — only on :data:`AgentEventType.CACHE_EVICTED`,
                    one of ``"ttl_expired"``,
                    ``"authority_expansion_bypass"``,
                    ``"raw_secret_leakage_bypass"``, or
                    ``"lru_capacity"``.

Defensive deep copies
---------------------

:class:`LLMDecisionFrame` carries mutable list fields
(``top_k_evidence``, ``selected_tool_surface``, ``current_blockers``,
``next_decision_options``, ``receipt_refs``) and dict fields
(``mission_card``, ``authority_card``, ``progress_card``,
``required_output_schema``). The cache stores and returns
:func:`copy.deepcopy` snapshots so that:

* a caller mutating a returned frame cannot mutate the cache's
  stored copy, and
* a caller mutating the original frame after :meth:`put` cannot
  retroactively change the cached state.

Authority property (Requirement 12.7)
-------------------------------------

The composite hash includes ``authority_hash``; a frame built under
different authority hashes to a different composite key and is
therefore a different cache entry. Cache reads can never silently
broaden the authority envelope of a downstream prompt — they only
return frames that the *original* builder produced under the
*original* authority. The :meth:`get` safety check on
``authority_expansion`` is a second, independent guard against
post-construction mutation of the cached frame.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from sentinel.agent.decision_frame import LLMDecisionFrame
from sentinel.shared.events import AgentEventType, EventBus

__all__ = [
    "CACHE_TYPE",
    "MAX_ENTRIES_PER_MISSION",
    "TTL_SECONDS",
    "LLMDecisionFrameCache",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


CACHE_TYPE: str = "frame"
"""Fixed ``cache_type`` tag used in every event emitted by this cache."""


MAX_ENTRIES_PER_MISSION: int = 128
"""LRU cap, enforced **per mission** (Requirement 9.2)."""


TTL_SECONDS: int = 600
"""TTL upper bound for cached frames in seconds (Requirement 9.7)."""


_TTL_NS: int = TTL_SECONDS * 1_000_000_000
"""TTL expressed in nanoseconds for comparison against monotonic clock."""


# Eviction reason tags. Defined as module constants so the test suite
# and any wiring layer can refer to them by name without string literals.
_REASON_TTL_EXPIRED: str = "ttl_expired"
_REASON_AUTHORITY_EXPANSION: str = "authority_expansion_bypass"
_REASON_RAW_SECRET_LEAKAGE: str = "raw_secret_leakage_bypass"
_REASON_LRU_CAPACITY: str = "lru_capacity"


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------


def _stable_hash(payload: dict[str, Any]) -> str:
    """Canonical SHA-256 hex digest of ``payload``.

    Identical to :func:`sentinel.agent.decision_frame._stable_hash` and
    the helpers in the sibling cache modules so any composite hash
    produced here is interchangeable with hashes elsewhere in the
    cognitive layer (sorted keys, no whitespace, ASCII escapes).

    The helper is duplicated privately rather than imported to keep
    :mod:`sentinel.perf.caches.llm_decision_frame_cache` self-contained
    — the cache module owns its hashing surface and does not pull in
    the decision-frame module's private helpers.
    """

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------


def _zero_stats() -> dict[str, int]:
    """Return a freshly zero-initialised counter dict for a new mission."""

    return {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "ttl_evictions": 0,
        "safety_bypasses": 0,
    }


# ---------------------------------------------------------------------------
# LLMDecisionFrameCache
# ---------------------------------------------------------------------------


class LLMDecisionFrameCache:
    """Per-mission LRU+TTL cache for :class:`LLMDecisionFrame` instances.

    Requirements: 2.3, 2.6, 9.1, 9.2, 9.4, 9.5, 9.6, 9.7, 12.2, 12.3.

    See the module docstring for storage layout, safety contract, event
    payload schema, and the per-mission LRU rationale.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._event_bus = event_bus
        self._clock = clock
        # Outer key: mission_id. Inner: OrderedDict for LRU semantics.
        self._entries: dict[str, OrderedDict[str, tuple[LLMDecisionFrame, int]]] = {}
        # Outer key: mission_id. Inner: counter dict.
        self._stats: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def composite_hash(
        self,
        *,
        mission_hot_hash: str,
        authority_hash: str,
        evidence_set_hash: str,
        tool_surface_hash: str,
    ) -> str:
        """Return the deterministic SHA-256 hex composite hash.

        The four inputs are hashed via :func:`_stable_hash` of a
        sorted-key dict so callers get a single opaque string suitable
        for use as the cache key. The key is opaque — callers must
        never reconstruct the inputs from it. Requirement 9.2.
        """

        return _stable_hash(
            {
                "mission_hot_hash": mission_hot_hash,
                "authority_hash": authority_hash,
                "evidence_set_hash": evidence_set_hash,
                "tool_surface_hash": tool_surface_hash,
            }
        )

    def get(self, composite: str, *, mission_id: str) -> LLMDecisionFrame | None:
        """Return a cached :class:`LLMDecisionFrame` or ``None``.

        Returns ``None`` (and emits the matching cache event) on:

        * composite-hash miss (Requirement 9.6) — increments ``misses``,
          emits :data:`AgentEventType.CACHE_MISS`.
        * TTL expired (Requirement 9.7) — increments ``ttl_evictions``,
          emits :data:`AgentEventType.CACHE_EVICTED` with
          ``reason="ttl_expired"``, removes the entry.
        * ``authority_expansion=True`` on the cached frame
          (Requirement 12.2) — increments ``safety_bypasses``, emits
          :data:`AgentEventType.CACHE_EVICTED` with
          ``reason="authority_expansion_bypass"``, removes the entry.
        * ``raw_secret_leakage=True`` on the cached frame
          (Requirement 12.3) — increments ``safety_bypasses``, emits
          :data:`AgentEventType.CACHE_EVICTED` with
          ``reason="raw_secret_leakage_bypass"``, removes the entry.

        On a clean hit: increments ``hits``, emits
        :data:`AgentEventType.CACHE_HIT`, promotes the entry to the
        LRU tail, and returns a defensive deep copy of the cached
        frame.
        """

        stats = self._stats_for(mission_id)
        bucket = self._entries.get(mission_id)

        if bucket is None or composite not in bucket:
            stats["misses"] += 1
            self._emit_miss(composite=composite, mission_id=mission_id)
            return None

        frame, created_at_ns = bucket[composite]

        # TTL check (Requirement 9.7). Compared in nanoseconds against
        # the monotonic clock to avoid wall-clock drift.
        if (self._clock() - created_at_ns) > _TTL_NS:
            del bucket[composite]
            stats["ttl_evictions"] += 1
            self._emit_evicted(
                composite=composite,
                mission_id=mission_id,
                reason=_REASON_TTL_EXPIRED,
            )
            return None

        # Safety bypass: authority_expansion (Requirement 12.2). Belt
        # and braces — ``put`` rejects authority_expansion=True writes,
        # but the cached frame may have been mutated post-store, so we
        # re-check here.
        if frame.authority_expansion:
            del bucket[composite]
            stats["safety_bypasses"] += 1
            self._emit_evicted(
                composite=composite,
                mission_id=mission_id,
                reason=_REASON_AUTHORITY_EXPANSION,
            )
            return None

        # Safety bypass: raw_secret_leakage (Requirement 12.3).
        if frame.raw_secret_leakage:
            del bucket[composite]
            stats["safety_bypasses"] += 1
            self._emit_evicted(
                composite=composite,
                mission_id=mission_id,
                reason=_REASON_RAW_SECRET_LEAKAGE,
            )
            return None

        # Clean hit (Requirement 9.5).
        bucket.move_to_end(composite)
        stats["hits"] += 1
        self._emit_hit(composite=composite, mission_id=mission_id)
        return copy.deepcopy(frame)

    def put(self, composite: str, frame: LLMDecisionFrame, *, mission_id: str) -> None:
        """Store ``frame`` under ``composite`` for ``mission_id``.

        Requirement 12.2 — rejects ``frame.authority_expansion=True``
        writes with a ``ValueError``. The frame is never stored in any
        form when this guard fires.

        Per-mission LRU enforcement (Requirement 9.2): if storing the
        new entry would exceed :data:`MAX_ENTRIES_PER_MISSION`, the
        oldest entries are evicted in FIFO order until the bucket size
        is back within bounds. Each LRU eviction increments
        ``evictions`` and emits
        :data:`AgentEventType.CACHE_EVICTED` with
        ``reason="lru_capacity"``.

        ``frame`` is :func:`copy.deepcopy`-ed before storage so a
        caller mutating the original frame after :meth:`put` cannot
        retroactively change the cached state.
        """

        if frame.authority_expansion:
            raise ValueError(
                "LLMDecisionFrameCache cannot store frames with authority_expansion=True"
            )

        bucket = self._entries.get(mission_id)
        if bucket is None:
            bucket = OrderedDict()
            self._entries[mission_id] = bucket

        # If we are overwriting an existing key, drop the old entry
        # first so the new one moves to the LRU tail without inflating
        # the bucket beyond the cap.
        if composite in bucket:
            del bucket[composite]

        bucket[composite] = (copy.deepcopy(frame), self._clock())
        self._enforce_capacity(mission_id=mission_id, bucket=bucket)

    def stats(self, mission_id: str) -> dict[str, int]:
        """Return the per-mission counter dict (Requirement 9.4).

        If the mission has never appeared in this cache, returns a
        zero-initialised counter dict. The returned dict is a fresh
        copy — callers cannot mutate the cache's internal state by
        mutating the result.
        """

        if mission_id not in self._stats:
            return _zero_stats()
        return dict(self._stats[mission_id])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stats_for(self, mission_id: str) -> dict[str, int]:
        """Return the live counter dict for ``mission_id`` (creating it lazily)."""

        if mission_id not in self._stats:
            self._stats[mission_id] = _zero_stats()
        return self._stats[mission_id]

    def _enforce_capacity(
        self,
        *,
        mission_id: str,
        bucket: OrderedDict[str, tuple[LLMDecisionFrame, int]],
    ) -> None:
        """LRU eviction: drop oldest entries in this mission's bucket.

        Per-mission only — does not touch any other mission's bucket.
        Each eviction increments the mission's ``evictions`` counter
        and emits a :data:`AgentEventType.CACHE_EVICTED` event with
        ``reason="lru_capacity"``.
        """

        stats = self._stats_for(mission_id)
        while len(bucket) > MAX_ENTRIES_PER_MISSION:
            evicted_key, _ = bucket.popitem(last=False)
            stats["evictions"] += 1
            self._emit_evicted(
                composite=evicted_key,
                mission_id=mission_id,
                reason=_REASON_LRU_CAPACITY,
            )

    # ------------------------------------------------------------------
    # Event emission helpers (payload whitelist enforced here)
    # ------------------------------------------------------------------

    def _emit_hit(self, *, composite: str, mission_id: str) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_HIT,
            "llm_decision_frame_cache hit",
            payload={
                "cache_type": CACHE_TYPE,
                "composite": composite,
                "mission_id": mission_id,
            },
        )

    def _emit_miss(self, *, composite: str, mission_id: str) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_MISS,
            "llm_decision_frame_cache miss",
            payload={
                "cache_type": CACHE_TYPE,
                "composite": composite,
                "mission_id": mission_id,
            },
        )

    def _emit_evicted(self, *, composite: str, mission_id: str, reason: str) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_EVICTED,
            "llm_decision_frame_cache evicted",
            payload={
                "cache_type": CACHE_TYPE,
                "composite": composite,
                "mission_id": mission_id,
                "reason": reason,
            },
        )
