"""Cache invalidation policy with dependency-graph traversal and TTL bounds.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Provides dependency-graph-primary invalidation with TTL upper bounds.
The dependency graph is traversed same-tick (BFS) on invalidation.
Access to invalidated-but-not-yet-evicted entries returns a cache miss.
Bulk eviction warnings are emitted when cause is INVALIDATION_EVENT and
evicted count exceeds 1000.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from sentinel.shared.events import AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

CacheKey = str
"""Opaque string identifier for a cache entry."""

# ---------------------------------------------------------------------------
# Valid TTL categories
# ---------------------------------------------------------------------------

_VALID_TTL_CATEGORIES = frozenset(
    {"workspace_snapshot", "evidence_selection", "prompt_frame", "decision_frame"}
)

# ---------------------------------------------------------------------------
# CacheEntry — internal mutable state (NOT a pydantic model)
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    """Internal mutable cache entry."""

    key: CacheKey
    value: Any
    ttl_category: str
    created_at_ns: int
    invalidated: bool = field(default=False)


# ---------------------------------------------------------------------------
# CacheInvalidationPolicy
# ---------------------------------------------------------------------------


class CacheInvalidationPolicy:
    """Dependency-graph-primary invalidation with TTL upper bounds.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """

    # TTL constants (seconds)
    TTL_WORKSPACE_SNAPSHOT_S = 300
    TTL_EVIDENCE_SELECTION_S = 600
    TTL_PROMPT_FRAME_S = 600
    TTL_DECISION_FRAME_S = 600

    # Bulk eviction warning threshold
    BULK_EVICTION_WARN_THRESHOLD = 1000

    # TTL map: category -> nanoseconds
    _TTL_NS: dict[str, int] = {
        "workspace_snapshot": 300 * 10**9,
        "evidence_selection": 600 * 10**9,
        "prompt_frame": 600 * 10**9,
        "decision_frame": 600 * 10**9,
    }

    def __init__(
        self,
        *,
        event_bus: EventBus,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._entries: dict[CacheKey, CacheEntry] = {}
        self._deps: dict[CacheKey, set[CacheKey]] = {}  # parent -> children
        self._event_bus = event_bus
        self._clock = clock

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_dependency(self, parent: CacheKey, child: CacheKey) -> None:
        """Register a dependency: invalidating *parent* also invalidates *child*."""
        if parent not in self._deps:
            self._deps[parent] = set()
        self._deps[parent].add(child)

    def put(self, key: CacheKey, value: Any, *, ttl_category: str) -> None:
        """Store a cache entry. Overwrites if key already exists.

        Raises ValueError if ttl_category is not one of the four valid categories.
        """
        if ttl_category not in _VALID_TTL_CATEGORIES:
            raise ValueError(
                f"Invalid ttl_category {ttl_category!r}. "
                f"Must be one of {sorted(_VALID_TTL_CATEGORIES)}."
            )
        self._entries[key] = CacheEntry(
            key=key,
            value=value,
            ttl_category=ttl_category,
            created_at_ns=self._clock(),
        )

    def get(self, key: CacheKey) -> Any | None:
        """Retrieve a cached value, or None on miss.

        Returns None (miss) if:
        - Key not in cache
        - Entry is already invalidated
        - TTL has expired (marks entry as invalidated on access)
        """
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.invalidated:
            return None

        # Check TTL expiry
        elapsed_ns = self._clock() - entry.created_at_ns
        ttl_ns = self._TTL_NS[entry.ttl_category]
        if elapsed_ns > ttl_ns:
            entry.invalidated = True
            return None

        return entry.value

    def invalidate(self, key: CacheKey, cause: str) -> int:
        """Invalidate a key and all transitive dependents (BFS).

        Returns the total count of entries marked as invalidated in this pass.
        Emits CACHE_INVALIDATION_BULK_WARNING if cause == "INVALIDATION_EVENT"
        and evicted count > BULK_EVICTION_WARN_THRESHOLD.
        """
        evicted_count = 0
        visited: set[CacheKey] = set()
        queue: deque[CacheKey] = deque()
        queue.append(key)

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            # Mark entry as invalidated if it exists and isn't already
            entry = self._entries.get(current)
            if entry is not None and not entry.invalidated:
                entry.invalidated = True
                evicted_count += 1

            # Traverse children
            children = self._deps.get(current)
            if children:
                for child in children:
                    if child not in visited:
                        queue.append(child)

        # Emit bulk warning if applicable
        if (
            cause == "INVALIDATION_EVENT"
            and evicted_count > self.BULK_EVICTION_WARN_THRESHOLD
        ):
            self._event_bus.append(
                event_type=AgentEventType.CACHE_INVALIDATION_BULK_WARNING,
                summary=(
                    f"Bulk cache invalidation: {evicted_count} entries evicted "
                    f"(cause={cause})"
                ),
                payload={"cause": cause, "evicted_count": evicted_count},
            )

        return evicted_count

    def evict_invalidated(self) -> int:
        """Remove all invalidated entries from the store. Returns count removed.

        Useful for memory reclamation.
        """
        to_remove = [k for k, e in self._entries.items() if e.invalidated]
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)
