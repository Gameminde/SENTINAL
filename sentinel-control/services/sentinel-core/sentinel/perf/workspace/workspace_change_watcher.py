"""``WorkspaceChangeWatcher`` and ``WorkspaceDelta`` — Phase E interface only.

# Feature: sentinel-performance-runtime-foundation, Phase E Task 10.1: WorkspaceChangeWatcher + WorkspaceDelta interface

This module installs the *interface and types* for the workspace-delta
subsystem that Phase E (Task 10.2) and the cache-invalidation chain
(Phase B) will consume. It is intentionally a passive container in this
task: no real filesystem-watcher backend (``watchdog`` /
``ReadDirectoryChangesW``) is wired, no poll-fallback thread is spawned,
no ``CacheInvalidationPolicy`` reference is touched, and no
``EventBus`` events are emitted. The real backend lands in a later
integration task.

The only way to enqueue a delta in this task is the ``push_delta`` API —
which is documented as a test/integration seam, not a production
producer. Downstream code (``WorkspaceSnapshotCache.apply_delta``,
Task 10.2) drains deltas via ``events()``; nothing in this file imports
or calls any cache module.

Layering rule (``sentinel/perf/__init__.py``)
---------------------------------------------

    measure --> hot_cold --> caches / sched / workspace --> bench

``workspace`` may import from ``measure`` and ``hot_cold`` only.
This module imports from neither — it depends only on
``sentinel.shared.models.SentinelModel`` for the frozen pydantic base
that every Sentinel data shape uses. That keeps the file additive,
side-effect-free at import time, and free of any
``CacheInvalidationPolicy`` / ``WorkspaceSnapshotCache`` / ``EventBus``
coupling per the Task 10.1 phase gate.

Validator semantics (``WorkspaceDelta``)
----------------------------------------

The ``WorkspaceDelta`` model is frozen and ``extra='forbid'``. A single
``model_validator(mode='after')`` enforces five structural invariants
that every downstream consumer relies on:

1. ``RENAMED`` deltas MUST carry ``previous_path`` non-None and not
   equal to ``path`` (the delta describes a move; identical paths would
   be a no-op).
2. Non-``RENAMED`` deltas MUST have ``previous_path is None``
   (``previous_path`` is meaningful only for renames; a stray value on
   a CREATED/MODIFIED/DELETED delta is a bug, not a feature).
3. ``DELETED`` deltas MUST have ``mtime_ns == 0``, ``size == 0``, and
   ``content_sha256 is None`` — the file no longer exists, so the
   filesystem metadata is unknowable and must be filled with sentinels.
4. ``CREATED`` and ``MODIFIED`` deltas MUST have ``mtime_ns >= 0``,
   ``size >= 0``, and ``content_sha256 is not None``. The watcher must
   capture the new content hash so the snapshot cache can update its
   ``snapshot_id`` deterministically (Task 10.2, Requirement 3.2).
5. ``RENAMED`` deltas MUST have a non-empty ``path`` (the new
   destination path). ``mtime_ns`` / ``size`` / ``content_sha256`` MAY
   be populated when the watcher knows them post-rename, but the
   validator does not strictly require it — pure renames without a
   content read are valid.

Requirements: 3.2.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, model_validator

from sentinel.shared.models import SentinelModel


class WorkspaceDelta(SentinelModel):
    """Single filesystem change event.

    Frozen pydantic model. The ``type`` discriminator selects which
    fields are meaningful — see the validator on this class for the
    five structural invariants every downstream consumer relies on.

    Field semantics
    ---------------
    * ``type`` — one of ``CREATED | MODIFIED | RENAMED | DELETED``.
    * ``path`` — for ``CREATED`` / ``MODIFIED`` / ``DELETED``, the
      affected path; for ``RENAMED``, the *new* path.
    * ``previous_path`` — populated only for ``RENAMED`` (the old
      path). MUST be ``None`` for the other three event types.
    * ``mtime_ns`` — filesystem mtime at detection (``0`` for
      ``DELETED``).
    * ``size`` — file size in bytes at detection (``0`` for
      ``DELETED``).
    * ``content_sha256`` — SHA-256 hex digest of the file body at
      detection. ``None`` for ``DELETED``; required for ``CREATED`` /
      ``MODIFIED``; optional for ``RENAMED``.
    * ``detected_at_ns`` — ``time.monotonic_ns()`` timestamp captured
      at detection. Provided by the producer; the validator does not
      enforce a value range so callers can use synthetic clocks in
      tests.

    Requirements: 3.2.
    """

    type: Literal["CREATED", "MODIFIED", "RENAMED", "DELETED"]
    path: str
    previous_path: str | None
    mtime_ns: int
    size: int
    content_sha256: str | None
    detected_at_ns: int

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _validate_event_shape(self) -> WorkspaceDelta:
        """Enforce the five structural invariants documented above."""
        # Invariant 1 + 5: RENAMED carries non-empty path AND a
        # previous_path that differs from path.
        if self.type == "RENAMED":
            if not self.path:
                raise ValueError(
                    "WorkspaceDelta(type='RENAMED') requires a non-empty 'path'."
                )
            if self.previous_path is None:
                raise ValueError(
                    "WorkspaceDelta(type='RENAMED') requires "
                    "'previous_path' to be non-None."
                )
            if self.previous_path == self.path:
                raise ValueError(
                    "WorkspaceDelta(type='RENAMED') requires "
                    "'previous_path' != 'path'."
                )
        else:
            # Invariant 2: non-RENAMED never carries a previous_path.
            if self.previous_path is not None:
                raise ValueError(
                    f"WorkspaceDelta(type={self.type!r}) must have "
                    "'previous_path is None'; previous_path is meaningful "
                    "only for RENAMED."
                )

        # Invariant 3: DELETED zeros out fs metadata.
        if self.type == "DELETED":
            if self.mtime_ns != 0:
                raise ValueError(
                    "WorkspaceDelta(type='DELETED') requires 'mtime_ns == 0'."
                )
            if self.size != 0:
                raise ValueError(
                    "WorkspaceDelta(type='DELETED') requires 'size == 0'."
                )
            if self.content_sha256 is not None:
                raise ValueError(
                    "WorkspaceDelta(type='DELETED') requires "
                    "'content_sha256 is None'."
                )

        # Invariant 4: CREATED / MODIFIED carry non-negative metadata
        # AND a content hash.
        if self.type in ("CREATED", "MODIFIED"):
            if self.mtime_ns < 0:
                raise ValueError(
                    f"WorkspaceDelta(type={self.type!r}) requires "
                    "'mtime_ns >= 0'."
                )
            if self.size < 0:
                raise ValueError(
                    f"WorkspaceDelta(type={self.type!r}) requires "
                    "'size >= 0'."
                )
            if self.content_sha256 is None:
                raise ValueError(
                    f"WorkspaceDelta(type={self.type!r}) requires "
                    "'content_sha256' to be non-None."
                )

        return self


class WorkspaceChangeWatcher:
    """Native fs watcher (watchdog / ReadDirectoryChangesW) with poll fallback.

    Phase E Task 10.1 — interface and types only.

    Real backend subscription is NOT wired in this task. The
    ``start(root)`` method records the root and prepares the in-memory
    structures; ``events()`` drains pending deltas FIFO; ``push_delta``
    is the only way to inject events in this task. The real
    filesystem-watcher backend (``watchdog`` /
    ``ReadDirectoryChangesW`` / poll fallback driven by
    ``poll_interval_s``) lands in a later integration task.

    No background thread, no asyncio task, no process, no
    ``CacheInvalidationPolicy`` / ``WorkspaceSnapshotCache`` /
    ``EventBus`` coupling — this is a passive container.

    Thread-safety
    -------------
    The pending-delta buffer is a ``collections.deque`` guarded by a
    ``threading.Lock``. ``push_delta`` and ``events()`` are safe to
    call from any thread; the lock is held only for the duration of a
    deque mutation, so there is no risk of contention with future
    backend producers.

    Requirements: 3.2.
    """

    def __init__(self, *, poll_interval_s: float = 0.25) -> None:
        if poll_interval_s <= 0:
            raise ValueError(
                "WorkspaceChangeWatcher.poll_interval_s must be > 0."
            )
        # Stored for the future poll-fallback backend. The current task
        # never reads this value at runtime; it is exposed via
        # ``poll_interval_s`` so tests and integration code can verify
        # construction-time configuration without poking private state.
        self._poll_interval_s: float = poll_interval_s
        self._root: Path | None = None
        self._started: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._pending: deque[WorkspaceDelta] = deque()

    # ------------------------------------------------------------------
    # Configuration accessor
    # ------------------------------------------------------------------

    @property
    def poll_interval_s(self) -> float:
        """Configured poll-fallback interval in seconds (read-only)."""
        return self._poll_interval_s

    @property
    def root(self) -> Path | None:
        """Resolved absolute root path, or ``None`` before ``start``."""
        return self._root

    @property
    def is_started(self) -> bool:
        """Whether ``start`` has been called without a matching ``stop``."""
        return self._started

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, root: Path) -> None:
        """Record the watcher root and mark the watcher as started.

        Validates that ``root`` exists and is a directory, resolves it
        to an absolute path via ``Path(root).resolve()``, and stores it
        on the instance. Calling ``start`` a second time without an
        intervening ``stop`` raises ``RuntimeError`` — the watcher is a
        single-root container and re-starting silently would mask a
        bug at the call site.

        No background thread, no asyncio task, no process is started
        in this task. Real backend wiring lands in a later integration
        task.
        """
        if self._started:
            raise RuntimeError("WorkspaceChangeWatcher already started")
        resolved = Path(root).resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"WorkspaceChangeWatcher root does not exist: {resolved}"
            )
        if not resolved.is_dir():
            raise NotADirectoryError(
                f"WorkspaceChangeWatcher root is not a directory: {resolved}"
            )
        self._root = resolved
        self._started = True

    def stop(self) -> None:
        """Stop the watcher; idempotent.

        No-op if ``start`` was never called. Clears the pending-delta
        queue and the started flag so a subsequent ``start`` begins
        from a clean state.
        """
        with self._lock:
            self._pending.clear()
        self._started = False
        self._root = None

    # ------------------------------------------------------------------
    # Delta plumbing
    # ------------------------------------------------------------------

    def push_delta(self, delta: WorkspaceDelta) -> None:
        """Enqueue a single delta for FIFO drainage by ``events()``.

        Test/integration seam — the real backend will eventually feed
        deltas through this same method. ``push_delta`` is callable
        before ``start`` (the watcher is a passive container; the
        ``start`` flag exists for the future backend, not for the
        in-memory queue).
        """
        with self._lock:
            self._pending.append(delta)

    def events(self) -> Iterator[WorkspaceDelta]:
        """Drain the pending-delta buffer FIFO.

        Returns a generator that yields every currently-buffered delta
        in insertion order, removing each one from the internal queue
        as it is yielded. Calling ``events()`` before ``start`` returns
        an empty iterator (no error) — the queue is simply empty.

        Deltas pushed *during* iteration are not included in the
        current generator; the snapshot of pending deltas is taken
        once at the start of iteration. Callers that want to drain a
        constantly-fed queue should re-call ``events()``.
        """
        # Snapshot under lock so concurrent ``push_delta`` calls do not
        # mutate the deque mid-drain. The snapshot is a list (not the
        # deque itself), so subsequent ``push_delta`` calls land in a
        # fresh deque state for the next ``events()`` call.
        with self._lock:
            snapshot = list(self._pending)
            self._pending.clear()
        for delta in snapshot:
            yield delta


__all__ = [
    "WorkspaceChangeWatcher",
    "WorkspaceDelta",
]
