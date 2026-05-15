"""``WorkspaceSnapshotCache`` — incremental snapshot driven by ``WorkspaceDelta``.

# Feature: sentinel-performance-runtime-foundation, Phase E Task 10.2: WorkspaceSnapshotCache incremental snapshot_id + apply_delta

This module owns the in-memory file-set view for a single workspace
root and produces a deterministic ``snapshot_id`` that downstream
caches (``ContextBuildCache``) compose into their composite keys via
``P-C-KEY-01``. It is fed by ``WorkspaceChangeWatcher`` deltas drained
by the caller; this module never subscribes to a real filesystem
watcher (same Phase E gate as Task 10.1).

Layering rule (``sentinel/perf/__init__.py``)
---------------------------------------------

    measure --> hot_cold --> caches / sched / workspace --> bench

``workspace`` may import from ``measure`` and ``hot_cold`` only. This
module imports the existing ``CacheInvalidationPolicy`` (read-only —
the policy module itself is *not* modified by Task 10.2) and the
``WorkspaceDelta`` / ``SentinelModel`` types. No ``EventBus`` import,
no ``ContextBuildCache`` import, no ``LLMDecisionFrameCache`` import,
no real fs-watcher backend.

snapshot_id semantics
---------------------

``snapshot_id`` is the SHA-256 hex digest of a canonical
serialization of the snapshot's files. The serialization is:

    rows = sorted lexicographically by *normalized* path
    each row = "{path}\\t{mtime_ns}\\t{size}\\t{content_sha256}"
    payload = "\\x1e".join(rows).encode("utf-8")
    snapshot_id = sha256(payload).hexdigest()

The empty-snapshot ``snapshot_id`` is therefore a fixed hex constant
(``sha256(b"")``). A no-op ``apply_delta`` (e.g. ``MODIFIED`` with
metadata identical to the currently-tracked tuple, or ``DELETED`` for
a path the snapshot never tracked) does NOT change ``snapshot_id``.
This is the "changes only when ``apply_delta`` actually mutates the
snapshot" guarantee from the design.

apply_delta semantics
---------------------

``apply_delta`` is single-writer (a snapshot cache instance is bound
to one mission's view; concurrent deltas from the same backend are
serialized through ``WorkspaceChangeWatcher.events()`` drainage). The
internal lock guards mutation against concurrent ``snapshot_id`` /
``files`` / ``has_path`` reads so readers always observe a consistent
state.

Per-type behavior:

* ``CREATED`` — insert ``(mtime_ns, size, content_sha256)`` under the
  normalized path. If the path is already tracked, raise
  ``ValueError`` (``CREATED`` on a tracked path is a producer bug; the
  watcher should have emitted ``MODIFIED``).
* ``MODIFIED`` — replace the metadata tuple under the normalized path.
  If the path is missing, raise ``ValueError``. If the new tuple is
  byte-identical to the existing one, the snapshot mutation is a
  no-op (``snapshot_id`` does not change), BUT the policy is still
  invalidated for the path key — Requirement 3.2 wording is
  unconditional: "WHEN a file is content-modified, THE policy SHALL
  invalidate". Documenting this explicitly so future readers do not
  mistake the idempotent ``snapshot_id`` for an absence of
  invalidation.
* ``RENAMED`` — remove ``previous_path``, insert ``path`` with the
  delta's metadata. If ``previous_path`` is missing in the snapshot,
  raise ``ValueError``. If the new ``path`` is already tracked
  (overwrite-on-rename), raise ``ValueError``. Both old and new path
  keys are invalidated.
* ``DELETED`` — remove the normalized path. If the path is not
  tracked, the call is a no-op (no exception, no invalidation, no
  ``snapshot_id`` change) — the watcher saw an event for a file
  outside what this snapshot ever tracked, so there is nothing to
  evict.

Invalidation key shapes
-----------------------

After a successful mutation the cache calls
``CacheInvalidationPolicy.invalidate(key, cause="INVALIDATION_EVENT")``
on:

* ``f"workspace_path:{normalized_path}"`` (``CREATED``, ``MODIFIED``,
  ``DELETED``).
* ``f"workspace_path:{normalized_previous_path}"`` AND
  ``f"workspace_path:{normalized_path}"`` (``RENAMED``).

When the snapshot composition actually changes (i.e. ``snapshot_id``
moved), the cache also invalidates
``f"workspace_snapshot:{snapshot_id_before_change}"`` so any dependent
that registered against the prior snapshot id is evicted in the same
tick. After invalidation, the new generation is registered via
``CacheInvalidationPolicy.put(f"workspace_snapshot:{snapshot_id_after_change}", snapshot_id_after_change, ttl_category="workspace_snapshot")``
so the 300 s TTL upper bound from Requirement 3.4 applies.

The cause string ``"INVALIDATION_EVENT"`` is the canonical bulk-warning
trigger from ``CacheInvalidationPolicy`` (the policy emits
``CACHE_INVALIDATION_BULK_WARNING`` only when cause is
``INVALIDATION_EVENT`` and evicted count > 1000 — see Requirement
3.6).

Path normalization
------------------

``WorkspaceDelta`` does not constrain its ``path`` / ``previous_path``
to absolute or normalized form (the validator only enforces structural
invariants per event type). The snapshot cache owns its own
normalization: every path is run through ``Path(p).as_posix()`` to
collapse Windows backslashes onto forward slashes for cross-platform
deterministic key shapes. This means
``workspace_path:src/foo.py`` is the canonical key whether the
watcher reported ``src\\foo.py`` (Windows) or ``src/foo.py`` (POSIX).

Boundaries (Phase E gate, Task 10.2 only)
-----------------------------------------

* No ``WorkspaceChangeWatcher.events()`` subscription inside
  ``apply_delta`` — callers drive the loop.
* No ``EventBus`` import; the ``CacheInvalidationPolicy`` already
  owns event emission.
* No ``ContextBuildCache`` / ``LLMDecisionFrameCache`` /
  ``PromptFrameCache`` coupling. ``ContextBuildCache.composite_key``
  integration into ``AgentRuntime`` is owned by ``P-C-KEY-01``, not
  Task 10.2.
* ``cache_invalidation_policy.py`` is not modified — this module
  consumes only its existing public API (``put``, ``invalidate``).

Requirements: 3.2, 3.4.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from sentinel.perf.hot_cold.cache_invalidation_policy import CacheInvalidationPolicy
from sentinel.perf.workspace.workspace_change_watcher import WorkspaceDelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INVALIDATION_CAUSE = "INVALIDATION_EVENT"
"""Canonical cause string for bulk-warning gating in CacheInvalidationPolicy."""

_TTL_CATEGORY_WORKSPACE_SNAPSHOT = "workspace_snapshot"
"""TTL category from CacheInvalidationPolicy._VALID_TTL_CATEGORIES (300 s upper bound)."""

_RECORD_SEPARATOR = "\x1e"
"""ASCII record separator for canonical snapshot serialization."""

_FIELD_SEPARATOR = "\t"
"""Tab between (path, mtime_ns, size, content_sha256) within a row."""


def _normalize_path(raw: str) -> str:
    """Return the cross-platform deterministic POSIX form of *raw*.

    Uses ``pathlib.Path(...).as_posix()`` which collapses Windows
    backslashes to forward slashes without resolving the path against
    the filesystem (no I/O, no ``resolve()``). This keeps the
    snapshot_id stable across operating systems and avoids accidental
    drift if the same logical file arrives as ``src\\foo.py`` from
    one watcher and ``src/foo.py`` from another.
    """
    return Path(raw).as_posix()


# ---------------------------------------------------------------------------
# WorkspaceSnapshotCache
# ---------------------------------------------------------------------------


class WorkspaceSnapshotCache:
    """Incremental view driven by ``WorkspaceChangeWatcher`` deltas.

    Phase E Task 10.2.

    The cache owns an in-memory ``dict[normalized_path, (mtime_ns,
    size, content_sha256)]`` and a cached ``snapshot_id`` (SHA-256 hex
    of the canonical serialization). ``apply_delta`` mutates the
    dict per the delta type, recomputes the cached ``snapshot_id``,
    and propagates invalidation to the injected
    ``CacheInvalidationPolicy``.

    Read accessors (``snapshot_id``, ``files``, ``has_path``) take
    the internal lock briefly to observe a consistent state with
    respect to a concurrent ``apply_delta``.

    Cache-key shapes registered by this module:

    * ``f"workspace_path:{normalized_path}"`` — invalidated on every
      mutation that touches the path.
    * ``f"workspace_snapshot:{snapshot_id}"`` — registered via
      ``put`` after every actual snapshot-id change; invalidated on
      the prior snapshot id when a mutation moves the snapshot.

    No other key shapes are introduced by this module.

    Requirements: 3.2, 3.4.
    """

    def __init__(
        self,
        *,
        invalidation_policy: CacheInvalidationPolicy,
    ) -> None:
        self._policy: CacheInvalidationPolicy = invalidation_policy
        # Normalized path -> (mtime_ns, size, content_sha256).
        self._files: dict[str, tuple[int, int, str]] = {}
        self._lock: threading.Lock = threading.Lock()
        # Cached snapshot_id; recomputed only when the dict mutates.
        # Initial empty-snapshot id is sha256(b"").hexdigest().
        self._snapshot_id: str = self._compute_snapshot_id_locked()

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    @property
    def snapshot_id(self) -> str:
        """Deterministic hex hash of the current snapshot.

        Changes only when ``apply_delta`` actually mutates the
        snapshot. Empty snapshot is the fixed constant
        ``sha256(b"").hexdigest()``.
        """
        with self._lock:
            return self._snapshot_id

    def files(self) -> tuple[tuple[str, int, int, str], ...]:
        """Return the sorted snapshot tuples ``(path, mtime_ns, size, content_sha256)``.

        Read-only view; callers cannot mutate the cache through the
        returned tuple. Sorted lexicographically by normalized path
        for deterministic comparison.
        """
        with self._lock:
            return tuple(
                (path, mtime_ns, size, content_sha256)
                for path, (mtime_ns, size, content_sha256) in sorted(
                    self._files.items()
                )
            )

    def has_path(self, path: str) -> bool:
        """Whether the normalized form of *path* is tracked in the snapshot."""
        normalized = _normalize_path(path)
        with self._lock:
            return normalized in self._files

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_delta(self, delta: WorkspaceDelta) -> None:
        """Mutate the snapshot per *delta* and propagate invalidation.

        See module docstring for per-type behavior. Validation errors
        (``CREATED`` on tracked path, ``MODIFIED`` on missing path,
        ``RENAMED`` with missing previous or conflicting new path)
        raise ``ValueError`` BEFORE any mutation or invalidation —
        the cache and the policy stay consistent on error paths.
        """
        with self._lock:
            previous_snapshot_id = self._snapshot_id
            keys_to_invalidate: list[str] = []
            mutated: bool = False

            if delta.type == "CREATED":
                normalized = _normalize_path(delta.path)
                if normalized in self._files:
                    raise ValueError(
                        f"WorkspaceSnapshotCache: CREATED on already-tracked "
                        f"path {normalized!r}; producer should emit MODIFIED."
                    )
                # Validator on WorkspaceDelta guarantees content_sha256 is not
                # None for CREATED, so the cast is safe.
                assert delta.content_sha256 is not None
                self._files[normalized] = (
                    delta.mtime_ns,
                    delta.size,
                    delta.content_sha256,
                )
                mutated = True
                keys_to_invalidate.append(f"workspace_path:{normalized}")

            elif delta.type == "MODIFIED":
                normalized = _normalize_path(delta.path)
                if normalized not in self._files:
                    raise ValueError(
                        f"WorkspaceSnapshotCache: MODIFIED on untracked "
                        f"path {normalized!r}; producer should emit CREATED."
                    )
                assert delta.content_sha256 is not None
                new_tuple = (delta.mtime_ns, delta.size, delta.content_sha256)
                if self._files[normalized] != new_tuple:
                    self._files[normalized] = new_tuple
                    mutated = True
                # Requirement 3.2 is unconditional for content-modified
                # events — invalidate the path key even if metadata is
                # byte-identical to the currently-tracked tuple. The
                # snapshot-id self-key is invalidated only when the
                # snapshot composition actually changes (see below).
                keys_to_invalidate.append(f"workspace_path:{normalized}")

            elif delta.type == "RENAMED":
                # The validator guarantees previous_path is not None and
                # differs from path for RENAMED.
                assert delta.previous_path is not None
                normalized_prev = _normalize_path(delta.previous_path)
                normalized_new = _normalize_path(delta.path)
                if normalized_prev not in self._files:
                    raise ValueError(
                        f"WorkspaceSnapshotCache: RENAMED with previous_path "
                        f"{normalized_prev!r} not tracked in snapshot."
                    )
                if normalized_new in self._files:
                    raise ValueError(
                        f"WorkspaceSnapshotCache: RENAMED target path "
                        f"{normalized_new!r} already tracked; refusing to "
                        f"overwrite."
                    )
                # The WorkspaceDelta validator allows RENAMED to omit a
                # content hash (pure rename, no content read by the
                # watcher). The snapshot cache requires every tracked
                # file to have a non-None content hash for snapshot_id
                # determinism, so we fork on the delta's content_sha256:
                #
                # * delta.content_sha256 is not None  -> the watcher did
                #   read the post-rename body; trust the full delta
                #   tuple (mtime_ns, size, content_sha256) verbatim.
                # * delta.content_sha256 is None      -> pure rename;
                #   the body is unchanged, so carry the previous
                #   tuple forward verbatim and just remap the key.
                existing = self._files[normalized_prev]
                if delta.content_sha256 is not None:
                    new_metadata = (
                        delta.mtime_ns,
                        delta.size,
                        delta.content_sha256,
                    )
                else:
                    new_metadata = existing
                del self._files[normalized_prev]
                self._files[normalized_new] = new_metadata
                mutated = True
                # Requirement 3.2: invalidate both old and new path keys.
                keys_to_invalidate.append(f"workspace_path:{normalized_prev}")
                keys_to_invalidate.append(f"workspace_path:{normalized_new}")

            elif delta.type == "DELETED":
                normalized = _normalize_path(delta.path)
                if normalized not in self._files:
                    # Watcher saw an event for a file outside what we
                    # tracked. No mutation, no invalidation, no
                    # snapshot_id change.
                    return
                del self._files[normalized]
                mutated = True
                keys_to_invalidate.append(f"workspace_path:{normalized}")

            else:  # pragma: no cover — Literal type guards against this
                raise ValueError(
                    f"WorkspaceSnapshotCache: unexpected delta type {delta.type!r}"
                )

            # Recompute the cached snapshot_id only when we actually
            # mutated the dict. MODIFIED with identical metadata leaves
            # the cached value untouched.
            if mutated:
                self._snapshot_id = self._compute_snapshot_id_locked()

            new_snapshot_id = self._snapshot_id

            # Invalidation order does not matter for correctness; the
            # policy's invalidate is BFS and same-tick. We collect all
            # keys then call the policy once per key with cause
            # INVALIDATION_EVENT so the bulk-warning rule from
            # Requirement 3.6 applies.
            for key in keys_to_invalidate:
                self._policy.invalidate(key, cause=_INVALIDATION_CAUSE)

            if new_snapshot_id != previous_snapshot_id:
                # Invalidate dependents of the prior snapshot generation
                # before registering the new one, so the eviction of
                # downstream entries (registered as dependents of
                # workspace_snapshot:{prior}) lands in the same tick.
                self._policy.invalidate(
                    f"workspace_snapshot:{previous_snapshot_id}",
                    cause=_INVALIDATION_CAUSE,
                )
                # Register the new generation under the workspace_snapshot
                # TTL category (300 s, Requirement 3.4). Any future
                # dependent registered against this key will be picked
                # up by the next invalidation pass.
                self._policy.put(
                    f"workspace_snapshot:{new_snapshot_id}",
                    new_snapshot_id,
                    ttl_category=_TTL_CATEGORY_WORKSPACE_SNAPSHOT,
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_snapshot_id_locked(self) -> str:
        """Compute SHA-256 hex of the canonical snapshot serialization.

        Caller MUST hold ``self._lock``. The serialization is:

            rows = sorted by normalized path (lexicographic, ascii)
            row  = "{path}\\t{mtime_ns}\\t{size}\\t{content_sha256}"
            payload = "\\x1e".join(rows).encode("utf-8")

        Empty snapshot serializes to ``b""`` and yields the fixed
        constant ``sha256(b"").hexdigest()`` —
        ``e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855``.
        """
        if not self._files:
            return hashlib.sha256(b"").hexdigest()
        rows = [
            f"{path}{_FIELD_SEPARATOR}{mtime_ns}{_FIELD_SEPARATOR}{size}"
            f"{_FIELD_SEPARATOR}{content_sha256}"
            for path, (mtime_ns, size, content_sha256) in sorted(
                self._files.items()
            )
        ]
        payload = _RECORD_SEPARATOR.join(rows).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


__all__ = [
    "WorkspaceSnapshotCache",
]
