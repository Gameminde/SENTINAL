"""ContextBuildCache — composite-key cache for AgentContext.

Task 6.1 / sentinel-performance-runtime-foundation.

Requirements: 2.1, 2.4, 2.5, 2.6, 3.1.

Scope summary
-------------

This module provides :class:`ContextBuildCache`, an LRU-bounded, in-memory
cache that maps a composite key built from
``(mission_hot_hash, workspace_snapshot_id, organ_state_hash, authority_hash)``
to a previously-built :class:`sentinel.agent.models.AgentContext`. The
cache exists so the cognitive cycle's :class:`ContextBuilder.build` does
not have to be replayed on every tick when its inputs are unchanged.

Equivalence model (Requirement 2.1)
-----------------------------------

The cache returns a result that is byte-identical to a fresh
``ContextBuilder.build`` *for the canonical deterministic form of the
AgentContext* — sorted keys, normalised whitespace, and volatile
timestamp-like fields excluded. ``AgentContext`` itself is mutable
(plain pydantic ``SentinelModel``), so the cache stores and returns
defensive deep copies; equivalence is measured against
:func:`_canonical_form`, never against raw object bytes.

Diagnostic mode (Requirement 2.4 / 2.5 / 2.6)
---------------------------------------------

When ``get_or_build(..., verify=True)`` is called, the cache executes
``builder()`` to produce a fresh context, compares
``_canonical_form(cached)`` to ``_canonical_form(fresh)``, and:

* on match — emits :data:`AgentEventType.CACHE_HIT` and returns a
  defensive deep copy of the cached entry;
* on divergence — emits
  :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` with payload
  ``{cache_type, composite_key, mismatch_description, mission_id}``
  (no context bodies, no raw payloads), evicts the cached entry,
  increments ``correctness_violations``, and returns the freshly-built
  context **without** a second recomputation. This matches the
  Property 3 invariant in the spec: a single fresh build settles the
  divergence.

Hard-constraint event payload schema (Requirement 12.1 / 12.8)
--------------------------------------------------------------

Events emitted by this cache **never** carry raw context bodies, raw
``user_input``, raw evidence content, raw artifact blobs, secrets, or
prompt text. Every payload is restricted to the whitelist:

* ``cache_type``           — fixed string ``"context"``;
* ``composite_key``        — the SHA-256 hex hash, not its inputs;
* ``mission_id``           — caller-supplied identifier or ``None``;
* ``mismatch_description`` — short human-readable string, only on the
  ``CACHE_CORRECTNESS_VIOLATION`` event.

Authority property (Requirement 12.7)
-------------------------------------

Cache hits never expand authority. The cache only stores and returns
contexts that the original ``builder()`` already produced. A context
built under different mission authority — i.e. a different
``authority_hash`` — yields a different composite key and is therefore
a different cache entry; cache reads can never silently broaden the
authority envelope of a downstream prompt.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from sentinel.agent.models import AgentContext
from sentinel.shared.events import AgentEventType, EventBus

__all__ = [
    "CACHE_TYPE",
    "CONTEXT_BUILD_CACHE_TTL_SECONDS",
    "DEFAULT_MAX_ENTRIES",
    "CacheKey",
    "ContextBuildCache",
]


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------


CacheKey = str
"""Opaque SHA-256 hex hash returned by ``ContextBuildCache.composite_key``."""


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


CACHE_TYPE: str = "context"
"""Fixed ``cache_type`` tag used in every event emitted by this cache.

Reused as the ``cache_type`` discriminator on
:data:`AgentEventType.CACHE_HIT`, :data:`AgentEventType.CACHE_MISS`,
:data:`AgentEventType.CACHE_EVICTED`, and
:data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION` events emitted on the
existing :class:`sentinel.shared.events.EventBus`.
"""

CONTEXT_BUILD_CACHE_TTL_SECONDS: int = 600
"""TTL upper bound (Requirement 3.4) for evidence selections.

This module does not enforce TTL eviction directly — TTL semantics are
the responsibility of :class:`CacheInvalidationPolicy` (Task 4.9). The
constant is exported here so the policy and any wiring layer share the
exact bound mandated by Requirement 3.4 ("600 seconds for evidence
selections").
"""

DEFAULT_MAX_ENTRIES: int = 256
"""Default LRU capacity for :class:`ContextBuildCache`."""


# ---------------------------------------------------------------------------
# Hash + canonicalisation helpers
# ---------------------------------------------------------------------------


def _stable_hash(payload: dict[str, Any]) -> str:
    """Canonical SHA-256 hex digest of ``payload``.

    Identical to :func:`sentinel.agent.decision_frame._stable_hash` so
    composite keys produced here are interchangeable with hashes
    elsewhere in the cognitive layer (sorted keys, no whitespace, ASCII
    escapes).
    """

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _strip_volatile_at_fields(value: Any, *, depth: int, max_depth: int) -> Any:
    """Walk ``value`` and remove dict keys ending in ``_at`` up to ``max_depth``.

    ``created_at`` and ``updated_at`` end in ``_at`` and are therefore
    covered by the suffix rule; the rule is conservative and only
    applies at depth ``<= max_depth`` to avoid stripping legitimate
    dict-shaped payloads buried deep in user input.
    """

    if isinstance(value, dict):
        if depth <= max_depth:
            return {
                key: _strip_volatile_at_fields(item, depth=depth + 1, max_depth=max_depth)
                for key, item in value.items()
                if not key.endswith("_at")
            }
        return {
            key: _strip_volatile_at_fields(item, depth=depth + 1, max_depth=max_depth)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_strip_volatile_at_fields(item, depth=depth + 1, max_depth=max_depth) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_volatile_at_fields(item, depth=depth + 1, max_depth=max_depth) for item in value)
    return value


def _canonical_form(context: AgentContext) -> dict[str, Any]:
    """Produce a normalised canonical dict from an :class:`AgentContext`.

    Normalisation rules
    -------------------

    1. ``context.model_dump(mode="json")`` is used as the base
       representation. ``mode="json"`` ensures enums, datetimes, and
       Decimals are coerced to JSON-compatible primitives so equality
       comparison is well-defined.
    2. Any dict key matching ``*_at`` (which covers ``created_at``,
       ``updated_at``, ``expires_at``, ``revoked_at``, and any other
       timestamp-shaped field name) is removed at depth <= 2.
       ``AgentContext.mission`` (a :class:`MissionAuthorityEnvelope`)
       carries ``created_at`` / ``expires_at`` / ``revoked_at``;
       stripping at depth <= 2 lets us drop those without touching
       deeply-nested user payloads.
    3. The resulting dict has insertion-order keys; equality is
       structural (Python ``==``), so order does not affect the
       comparison performed by :meth:`ContextBuildCache.get_or_build`
       in ``verify=True`` diagnostic mode.

    The returned dict is never reflected back into the EventBus and is
    not stored — it is computed on demand and discarded.
    """

    payload = context.model_dump(mode="json")
    return _strip_volatile_at_fields(payload, depth=0, max_depth=2)


# ---------------------------------------------------------------------------
# ContextBuildCache
# ---------------------------------------------------------------------------


class ContextBuildCache:
    """Caches :class:`AgentContext` by composite key with canonical equivalence.

    Requirements: 2.1, 2.4, 2.5, 2.6, 3.1.

    Storage discipline
    ------------------

    * Entries are stored in an :class:`collections.OrderedDict` and
      managed as a strict LRU: every read promotes the entry to the
      tail; on insert, the head is evicted while ``len > max_entries``.
    * Both stored and returned contexts pass through
      :func:`copy.deepcopy`. Mutating a returned context cannot mutate
      the cache's stored copy, and the builder's original return value
      cannot be mutated by a downstream consumer.

    Event discipline
    ----------------

    Every cache event payload is restricted to
    ``{cache_type, composite_key, mission_id}`` plus
    ``mismatch_description`` on the violation event. No raw context
    bodies, user input, evidence content, artifact bytes, or secrets
    ever appear in an event payload. See module docstring for the hard
    constraint statement.

    Authority preservation
    ----------------------

    The composite key contains ``authority_hash``; a context built
    under a different authority hashes to a different key. Cache reads
    therefore cannot expand the authority envelope of a downstream
    prompt — they only return contexts that the *original* builder
    produced under the *original* authority. ``stats()`` exposes the
    same hit/miss counters that :class:`CacheInvalidationPolicy` reads
    so downstream wiring can verify the cache is in steady state.
    """

    def __init__(self, *, event_bus: EventBus, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("ContextBuildCache.max_entries must be >= 1")
        self._event_bus = event_bus
        self._max_entries = max_entries
        self._entries: OrderedDict[CacheKey, AgentContext] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._correctness_violations = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def composite_key(
        self,
        *,
        mission_hot_hash: str,
        workspace_snapshot_id: str,
        organ_state_hash: str,
        authority_hash: str,
    ) -> CacheKey:
        """Return the deterministic SHA-256 hex composite key.

        The four inputs are hashed via :func:`_stable_hash` of a
        sorted-key dict so callers get a single opaque string suitable
        for use as the cache key. The key is otherwise opaque — callers
        must never reconstruct the inputs from it.
        """

        return _stable_hash(
            {
                "mission_hot_hash": mission_hot_hash,
                "workspace_snapshot_id": workspace_snapshot_id,
                "organ_state_hash": organ_state_hash,
                "authority_hash": authority_hash,
            }
        )

    def get_or_build(
        self,
        key: CacheKey,
        builder: Callable[[], AgentContext],
        *,
        verify: bool = False,
        mission_id: str | None = None,
    ) -> AgentContext:
        """Return a cached or freshly-built :class:`AgentContext`.

        * ``verify=False`` (production mode, Requirement 2.1):
          on cache hit emit :data:`AgentEventType.CACHE_HIT`, increment
          the hit counter, and return a defensive deep copy of the
          cached entry. On cache miss invoke ``builder()``, store a
          deep copy, evict the oldest entry if capacity is exceeded
          (each eviction emits :data:`AgentEventType.CACHE_EVICTED`),
          and return a deep copy of the fresh result.
        * ``verify=True`` (diagnostic mode, Requirement 2.4 / 2.5 /
          2.6): on cache hit invoke ``builder()`` and compare
          :func:`_canonical_form` of the cached entry to
          ``_canonical_form`` of the fresh build. On match, emit
          :data:`AgentEventType.CACHE_HIT` and return a deep copy of
          the cached entry. On divergence, emit
          :data:`AgentEventType.CACHE_CORRECTNESS_VIOLATION`, evict
          the entry, increment ``correctness_violations``, and return
          the fresh build (no second recompute). On cache miss, fall
          through to the ``verify=False`` miss path; ``builder()`` is
          invoked exactly once.

        ``mission_id`` is purely descriptive — it is forwarded into
        the event payload so downstream observers can correlate cache
        events with mission timelines without touching the context
        body.
        """

        if key in self._entries:
            cached = self._entries[key]
            self._entries.move_to_end(key)
            if verify:
                fresh = builder()
                if _canonical_form(cached) == _canonical_form(fresh):
                    self._hits += 1
                    self._emit_hit(key=key, mission_id=mission_id)
                    return copy.deepcopy(cached)
                # Divergence — evict, return fresh, do not recompute.
                self._correctness_violations += 1
                del self._entries[key]
                self._emit_correctness_violation(
                    key=key,
                    mission_id=mission_id,
                    mismatch_description=(
                        "context_build_cache canonical-form divergence between "
                        "cached AgentContext and fresh builder() output"
                    ),
                )
                return fresh
            self._hits += 1
            self._emit_hit(key=key, mission_id=mission_id)
            return copy.deepcopy(cached)

        # Cache miss
        self._misses += 1
        self._emit_miss(key=key, mission_id=mission_id)
        fresh = builder()
        self._entries[key] = copy.deepcopy(fresh)
        self._enforce_capacity()
        return copy.deepcopy(fresh)

    def invalidate(self, key: CacheKey) -> bool:
        """Remove ``key`` from the cache.

        Returns ``True`` if the entry existed and was removed (and a
        :data:`AgentEventType.CACHE_EVICTED` event was emitted),
        ``False`` if the key was not present (no event emitted).
        """

        if key not in self._entries:
            return False
        del self._entries[key]
        self._evictions += 1
        self._emit_evicted(key=key, mission_id=None)
        return True

    def stats(self) -> dict[str, int]:
        """Return current cache counters and size.

        Keys: ``hits``, ``misses``, ``evictions``,
        ``correctness_violations``, ``size``.
        """

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "correctness_violations": self._correctness_violations,
            "size": len(self._entries),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """LRU eviction: drop oldest until ``len <= max_entries``."""

        while len(self._entries) > self._max_entries:
            evicted_key, _ = self._entries.popitem(last=False)
            self._evictions += 1
            self._emit_evicted(key=evicted_key, mission_id=None)

    def _emit_hit(self, *, key: CacheKey, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_HIT,
            "context_build_cache hit",
            payload={
                "cache_type": CACHE_TYPE,
                "composite_key": key,
                "mission_id": mission_id,
            },
        )

    def _emit_miss(self, *, key: CacheKey, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_MISS,
            "context_build_cache miss",
            payload={
                "cache_type": CACHE_TYPE,
                "composite_key": key,
                "mission_id": mission_id,
            },
        )

    def _emit_evicted(self, *, key: CacheKey, mission_id: str | None) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_EVICTED,
            "context_build_cache evicted",
            payload={
                "cache_type": CACHE_TYPE,
                "composite_key": key,
                "mission_id": mission_id,
            },
        )

    def _emit_correctness_violation(
        self,
        *,
        key: CacheKey,
        mission_id: str | None,
        mismatch_description: str,
    ) -> None:
        self._event_bus.append(
            AgentEventType.CACHE_CORRECTNESS_VIOLATION,
            "context_build_cache canonical-form divergence",
            payload={
                "cache_type": CACHE_TYPE,
                "composite_key": key,
                "mismatch_description": mismatch_description,
                "mission_id": mission_id,
            },
        )
