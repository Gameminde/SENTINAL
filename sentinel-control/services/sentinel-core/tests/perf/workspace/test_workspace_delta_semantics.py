# Feature: sentinel-performance-runtime-foundation, Phase E Task 10.3: workspace delta semantics
"""Unit tests — ``WorkspaceDelta`` validator + ``WorkspaceChangeWatcher`` container + ``WorkspaceSnapshotCache.apply_delta`` + ``CacheInvalidationPolicy`` TTL semantics.

**Validates: Requirements 3.2, 3.4.**

This module is the deterministic-unit counterpart to the property-test
surface for the Phase E workspace subsystem (Tasks 10.1 + 10.2). It
verifies, line by line, the five structural invariants of
``WorkspaceDelta``, the passive-container semantics of
``WorkspaceChangeWatcher``, the per-type ``apply_delta`` behavior of
``WorkspaceSnapshotCache`` (including the policy-invalidation call
sequences), and the 300-second TTL upper bound on the
``workspace_snapshot`` category.

No production module is modified. No real ``watchdog`` /
``ReadDirectoryChangesW`` backend is instantiated. No filesystem I/O
beyond ``tmp_path``-rooted ``start``-validation tests. The
``CacheInvalidationPolicy`` spy is built by monkey-patching the bound
``invalidate`` / ``put`` methods of a single policy instance — the
policy module itself is left untouched.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.perf.hot_cold.cache_invalidation_policy import (
    CacheInvalidationPolicy,
)
from sentinel.perf.workspace.workspace_change_watcher import (
    WorkspaceChangeWatcher,
    WorkspaceDelta,
)
from sentinel.perf.workspace.workspace_snapshot_cache import (
    WorkspaceSnapshotCache,
)
from sentinel.shared.events import EventBus

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

_EMPTY_SNAPSHOT_ID = hashlib.sha256(b"").hexdigest()
"""Fixed snapshot_id for an empty WorkspaceSnapshotCache."""

_INVALIDATION_CAUSE = "INVALIDATION_EVENT"
"""Canonical cause string the cache passes to policy.invalidate."""

_HASH_A = "a" * 64
_HASH_B = "b" * 64
_HASH_C = "c" * 64


def _make_delta(
    *,
    type: str = "CREATED",
    path: str = "src/a.py",
    previous_path: str | None = None,
    mtime_ns: int = 100,
    size: int = 10,
    content_sha256: str | None = _HASH_A,
    detected_at_ns: int = 1,
) -> WorkspaceDelta:
    """Build a ``WorkspaceDelta`` with all fields explicit.

    Defaults are valid for ``type='CREATED'``. Tests override the
    fields they care about. This helper does not work around the
    validator — it just shortens the per-call construction so tests
    stay focused on the behavior under test.
    """
    return WorkspaceDelta(
        type=type,  # type: ignore[arg-type]
        path=path,
        previous_path=previous_path,
        mtime_ns=mtime_ns,
        size=size,
        content_sha256=content_sha256,
        detected_at_ns=detected_at_ns,
    )


def _make_deleted(path: str = "src/a.py") -> WorkspaceDelta:
    """Construct a valid DELETED delta for *path*."""
    return WorkspaceDelta(
        type="DELETED",
        path=path,
        previous_path=None,
        mtime_ns=0,
        size=0,
        content_sha256=None,
        detected_at_ns=2,
    )


# ---------------------------------------------------------------------------
# Fixture: (policy, cache, spy)
# ---------------------------------------------------------------------------


@pytest.fixture
def policy_cache(monkeypatch: pytest.MonkeyPatch):
    """Provide a ``(policy, cache, spy)`` tuple with monkey-patched call spies.

    The spy wraps ``policy.invalidate`` and ``policy.put`` so each test
    can assert the exact call sequence the
    ``WorkspaceSnapshotCache`` performed. The wrappers still delegate
    to the real bound methods so policy state (entries, dep graph,
    invalidation flags, TTL bookkeeping) stays correct — tests in
    Section D rely on that.

    ``spy.clock_holder`` is a single-element dict whose ``"now_ns"``
    field is the current monotonic-ns reading the policy uses. Tests
    advance the clock by mutating ``spy.clock_holder["now_ns"]``.
    """
    clock_holder: dict[str, int] = {"now_ns": 0}
    bus = EventBus(mission_id="m_workspace_test")
    policy = CacheInvalidationPolicy(
        event_bus=bus,
        clock=lambda: clock_holder["now_ns"],
    )

    invalidate_calls: list[tuple[str, str]] = []
    put_calls: list[tuple[str, Any, str]] = []

    real_invalidate = policy.invalidate
    real_put = policy.put

    def spy_invalidate(key: str, cause: str) -> int:
        invalidate_calls.append((key, cause))
        return real_invalidate(key, cause)

    def spy_put(key: str, value: Any, *, ttl_category: str) -> None:
        put_calls.append((key, value, ttl_category))
        return real_put(key, value, ttl_category=ttl_category)

    monkeypatch.setattr(policy, "invalidate", spy_invalidate)
    monkeypatch.setattr(policy, "put", spy_put)

    cache = WorkspaceSnapshotCache(invalidation_policy=policy)
    spy = SimpleNamespace(
        invalidate_calls=invalidate_calls,
        put_calls=put_calls,
        clock_holder=clock_holder,
        bus=bus,
    )
    return policy, cache, spy


# ===========================================================================
# Section A — WorkspaceDelta validator semantics
# ===========================================================================


def test_created_valid() -> None:
    """CREATED delta with all required fields constructs and round-trips.

    Validates Requirement 3.2 — the watcher must be able to emit a
    structurally-valid CREATED delta carrying the new content hash.
    """
    delta = _make_delta(type="CREATED", path="src/x.py", content_sha256=_HASH_A)
    dumped = delta.model_dump()
    rehydrated = WorkspaceDelta.model_validate(dumped)
    assert rehydrated == delta
    assert rehydrated.type == "CREATED"
    assert rehydrated.previous_path is None


def test_modified_valid() -> None:
    """MODIFIED delta with all required fields constructs and round-trips.

    Validates Requirement 3.2 — content-modify events carry the new
    hash so ``WorkspaceSnapshotCache`` can re-derive ``snapshot_id``.
    """
    delta = _make_delta(type="MODIFIED", path="src/x.py", content_sha256=_HASH_B)
    rehydrated = WorkspaceDelta.model_validate(delta.model_dump())
    assert rehydrated == delta
    assert rehydrated.type == "MODIFIED"
    assert rehydrated.previous_path is None


def test_renamed_valid() -> None:
    """RENAMED delta with previous_path != path constructs and round-trips.

    Validates Requirement 3.2 — rename events carry both legs of the
    move so the cache can drop the old key and insert the new one.
    """
    delta = WorkspaceDelta(
        type="RENAMED",
        path="src/new.py",
        previous_path="src/old.py",
        mtime_ns=200,
        size=20,
        content_sha256=_HASH_C,
        detected_at_ns=3,
    )
    rehydrated = WorkspaceDelta.model_validate(delta.model_dump())
    assert rehydrated == delta
    assert rehydrated.previous_path == "src/old.py"
    assert rehydrated.path == "src/new.py"


def test_deleted_valid() -> None:
    """DELETED delta with sentinel zero/None metadata constructs.

    Validates Requirement 3.2 — DELETED carries no fs metadata
    because the file no longer exists; the snapshot consumer must
    accept the documented sentinels.
    """
    delta = WorkspaceDelta(
        type="DELETED",
        path="src/x.py",
        previous_path=None,
        mtime_ns=0,
        size=0,
        content_sha256=None,
        detected_at_ns=4,
    )
    rehydrated = WorkspaceDelta.model_validate(delta.model_dump())
    assert rehydrated == delta
    assert rehydrated.mtime_ns == 0
    assert rehydrated.size == 0
    assert rehydrated.content_sha256 is None


def test_renamed_missing_previous_path_rejected() -> None:
    """RENAMED with previous_path=None violates Invariant 1.

    Validates Requirement 3.2 — a rename that does not carry the old
    path is structurally indistinguishable from a CREATED and must
    not be accepted by the validator.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="RENAMED",
            path="src/new.py",
            previous_path=None,
            mtime_ns=100,
            size=10,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


def test_renamed_same_path_rejected() -> None:
    """RENAMED with previous_path == path violates Invariant 1.

    Validates Requirement 3.2 — a rename to the same path is a no-op
    and is treated as a producer bug; the validator must reject it
    so the snapshot cache never receives a degenerate delta.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="RENAMED",
            path="src/x.py",
            previous_path="src/x.py",
            mtime_ns=100,
            size=10,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


def test_renamed_empty_path_rejected() -> None:
    """RENAMED with path='' violates Invariant 5.

    Validates Requirement 3.2 — the new destination path must be
    non-empty so downstream key-shape construction
    ``workspace_path:{path}`` is never an empty key.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="RENAMED",
            path="",
            previous_path="src/old.py",
            mtime_ns=100,
            size=10,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


@pytest.mark.parametrize("delta_type", ["CREATED", "MODIFIED", "DELETED"])
def test_non_renamed_with_previous_path_rejected(delta_type: str) -> None:
    """Non-RENAMED deltas reject any previous_path.

    Validates Requirement 3.2 — Invariant 2: previous_path is
    meaningful only for renames. A stray value on
    CREATED/MODIFIED/DELETED is a producer bug.
    """
    if delta_type == "DELETED":
        kwargs = {
            "mtime_ns": 0,
            "size": 0,
            "content_sha256": None,
        }
    else:
        kwargs = {
            "mtime_ns": 100,
            "size": 10,
            "content_sha256": _HASH_A,
        }
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type=delta_type,  # type: ignore[arg-type]
            path="src/x.py",
            previous_path="src/old.py",
            detected_at_ns=1,
            **kwargs,
        )


def test_deleted_with_nonzero_mtime_rejected() -> None:
    """DELETED with mtime_ns != 0 violates Invariant 3.

    Validates Requirement 3.2 — DELETED must carry mtime_ns == 0
    sentinel because the file no longer exists.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="DELETED",
            path="src/x.py",
            previous_path=None,
            mtime_ns=1,
            size=0,
            content_sha256=None,
            detected_at_ns=1,
        )


def test_deleted_with_nonzero_size_rejected() -> None:
    """DELETED with size != 0 violates Invariant 3.

    Validates Requirement 3.2 — DELETED must carry size == 0
    sentinel.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="DELETED",
            path="src/x.py",
            previous_path=None,
            mtime_ns=0,
            size=1,
            content_sha256=None,
            detected_at_ns=1,
        )


def test_deleted_with_content_sha256_rejected() -> None:
    """DELETED with non-None content_sha256 violates Invariant 3.

    Validates Requirement 3.2 — DELETED must carry
    content_sha256 is None because the body is unknowable.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type="DELETED",
            path="src/x.py",
            previous_path=None,
            mtime_ns=0,
            size=0,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


@pytest.mark.parametrize("delta_type", ["CREATED", "MODIFIED"])
def test_created_modified_without_content_sha256_rejected(delta_type: str) -> None:
    """CREATED / MODIFIED without content_sha256 violate Invariant 4.

    Validates Requirement 3.2 — content-bearing events must carry
    the new hash so ``WorkspaceSnapshotCache`` can re-derive
    ``snapshot_id`` deterministically.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type=delta_type,  # type: ignore[arg-type]
            path="src/x.py",
            previous_path=None,
            mtime_ns=100,
            size=10,
            content_sha256=None,
            detected_at_ns=1,
        )


@pytest.mark.parametrize("delta_type", ["CREATED", "MODIFIED"])
def test_created_modified_negative_mtime_rejected(delta_type: str) -> None:
    """CREATED / MODIFIED with mtime_ns < 0 violate Invariant 4.

    Validates Requirement 3.2 — fs metadata must be non-negative.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type=delta_type,  # type: ignore[arg-type]
            path="src/x.py",
            previous_path=None,
            mtime_ns=-1,
            size=10,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


@pytest.mark.parametrize("delta_type", ["CREATED", "MODIFIED"])
def test_created_modified_negative_size_rejected(delta_type: str) -> None:
    """CREATED / MODIFIED with size < 0 violate Invariant 4.

    Validates Requirement 3.2 — fs metadata must be non-negative.
    """
    with pytest.raises(ValidationError):
        WorkspaceDelta(
            type=delta_type,  # type: ignore[arg-type]
            path="src/x.py",
            previous_path=None,
            mtime_ns=100,
            size=-1,
            content_sha256=_HASH_A,
            detected_at_ns=1,
        )


def test_frozen_immutable() -> None:
    """Constructed delta is frozen — direct attribute mutation raises.

    Validates Requirement 3.2 — the delta is the canonical
    cross-thread carrier between the watcher producer and the
    snapshot-cache consumer; mutability would invalidate hashes
    computed downstream.
    """
    delta = _make_delta(type="CREATED", path="src/x.py")
    with pytest.raises(ValidationError):
        delta.path = "src/y.py"  # type: ignore[misc]


# ===========================================================================
# Section B — WorkspaceChangeWatcher passive container
# ===========================================================================


def test_events_before_start_empty() -> None:
    """Fresh watcher drains an empty iterator before ``start``.

    Validates Requirement 3.2 — the watcher is a passive container;
    calling ``events()`` on an unstarted watcher MUST NOT raise.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    assert list(watcher.events()) == []


def test_push_delta_before_start() -> None:
    """``push_delta`` works before ``start`` and drains FIFO afterwards.

    Validates Requirement 3.2 — ``push_delta`` is the test/integration
    seam; it does not gate on the started flag.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    d1 = _make_delta(path="src/a.py")
    d2 = _make_delta(path="src/b.py")
    watcher.push_delta(d1)
    watcher.push_delta(d2)
    assert list(watcher.events()) == [d1, d2]


def test_start_resolves_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``start`` resolves a relative path to an absolute path.

    Validates Requirement 3.2 — the watcher root must be unambiguous
    so downstream key shapes are stable across cwd changes.
    """
    sub = tmp_path / "watch_root"
    sub.mkdir()
    monkeypatch.chdir(tmp_path)
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    watcher.start(Path("watch_root"))
    assert watcher.root is not None
    assert watcher.root.is_absolute()
    assert watcher.root == sub.resolve()


def test_start_twice_raises(tmp_path: Path) -> None:
    """``start`` called twice without an intervening ``stop`` raises.

    Validates Requirement 3.2 — silently re-starting would mask a
    bug at the call site.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    watcher.start(tmp_path)
    with pytest.raises(RuntimeError):
        watcher.start(tmp_path)


def test_start_missing_path_raises(tmp_path: Path) -> None:
    """``start`` on a non-existent path raises ``FileNotFoundError``.

    Validates Requirement 3.2 — the watcher refuses to bind to a
    path the operating system cannot stat.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    with pytest.raises(FileNotFoundError):
        watcher.start(tmp_path / "does_not_exist")


def test_start_non_dir_raises(tmp_path: Path) -> None:
    """``start`` on a non-directory raises ``NotADirectoryError``.

    Validates Requirement 3.2 — a file is not a watchable root.
    """
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("hello", encoding="utf-8")
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    with pytest.raises(NotADirectoryError):
        watcher.start(file_path)


def test_stop_idempotent(tmp_path: Path) -> None:
    """``stop`` is safe to call repeatedly.

    Validates Requirement 3.2 — passive container; double-stop must
    not raise.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    watcher.start(tmp_path)
    watcher.stop()
    watcher.stop()
    assert watcher.is_started is False
    assert watcher.root is None


def test_stop_clears_queue(tmp_path: Path) -> None:
    """``stop`` clears the pending-delta queue.

    Validates Requirement 3.2 — a re-``start`` begins from a clean
    queue; deltas pushed before ``stop`` are not surfaced afterwards.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    watcher.push_delta(_make_delta(path="src/a.py"))
    watcher.push_delta(_make_delta(path="src/b.py"))
    watcher.start(tmp_path)
    watcher.stop()
    watcher.start(tmp_path)
    assert list(watcher.events()) == []


def test_events_drain_fifo() -> None:
    """``events()`` yields all buffered deltas in insertion order, then nothing.

    Validates Requirement 3.2 — FIFO drainage with snapshot
    semantics: the second call returns an empty iterator.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    d1 = _make_delta(path="src/a.py")
    d2 = _make_delta(path="src/b.py")
    d3 = _make_delta(path="src/c.py")
    watcher.push_delta(d1)
    watcher.push_delta(d2)
    watcher.push_delta(d3)
    assert list(watcher.events()) == [d1, d2, d3]
    assert list(watcher.events()) == []


def test_events_drain_concurrent_with_push() -> None:
    """A push during a partial drain lands in the next ``events()`` call.

    Validates Requirement 3.2 — ``events()`` snapshots under lock at
    the start of iteration. Deltas pushed concurrently mid-drain are
    not retro-injected into the in-flight generator; they appear in
    the next drain cycle. This is the documented "snapshot of
    pending deltas is taken once at the start of iteration"
    contract.
    """
    watcher = WorkspaceChangeWatcher(poll_interval_s=0.25)
    d1 = _make_delta(path="src/a.py")
    d2 = _make_delta(path="src/b.py")
    d3 = _make_delta(path="src/c.py")
    watcher.push_delta(d1)
    watcher.push_delta(d2)

    drained: list[WorkspaceDelta] = []
    first_yielded = threading.Event()
    can_finish = threading.Event()

    def drain() -> None:
        for delta in watcher.events():
            drained.append(delta)
            if len(drained) == 1:
                first_yielded.set()
                can_finish.wait(timeout=2.0)

    drainer = threading.Thread(target=drain)
    drainer.start()
    assert first_yielded.wait(timeout=2.0), "drainer did not yield first delta"
    # Push d3 while the drainer is paused after the first yield.
    watcher.push_delta(d3)
    can_finish.set()
    drainer.join(timeout=2.0)
    assert not drainer.is_alive(), "drainer thread did not finish"

    assert drained == [d1, d2]
    # Second drain returns the delta pushed concurrently.
    assert list(watcher.events()) == [d3]


def test_poll_interval_zero_rejected() -> None:
    """``poll_interval_s=0`` is rejected.

    Validates Requirement 3.2 — the poll-fallback interval must be
    strictly positive.
    """
    with pytest.raises(ValueError):
        WorkspaceChangeWatcher(poll_interval_s=0)


def test_poll_interval_negative_rejected() -> None:
    """``poll_interval_s<0`` is rejected.

    Validates Requirement 3.2 — negative intervals are nonsensical.
    """
    with pytest.raises(ValueError):
        WorkspaceChangeWatcher(poll_interval_s=-1)


# ===========================================================================
# Section C — WorkspaceSnapshotCache.apply_delta semantics (Requirement 3.2)
# ===========================================================================


def test_empty_snapshot_id_constant(policy_cache: tuple) -> None:
    """Empty cache exposes the fixed ``sha256(b"")`` snapshot_id.

    Validates Requirement 3.2 — the empty snapshot is a documented
    constant that downstream caches can rely on as the
    pre-population value.
    """
    _, cache, spy = policy_cache
    assert cache.snapshot_id == _EMPTY_SNAPSHOT_ID
    assert cache.files() == ()
    assert spy.invalidate_calls == []
    assert spy.put_calls == []


def test_created_inserts_and_invalidates(policy_cache: tuple) -> None:
    """CREATED inserts the path and invalidates ``workspace_path:<path>``.

    Validates Requirement 3.2 — content-creation events
    invalidate the path key, change the snapshot id, invalidate the
    prior snapshot id, and register the new snapshot id under the
    ``workspace_snapshot`` TTL category.
    """
    _, cache, spy = policy_cache
    prev_id = cache.snapshot_id
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))

    assert cache.has_path("src/a.py") is True
    new_id = cache.snapshot_id
    assert new_id != prev_id

    # workspace_path:src/a.py invalidated
    assert ("workspace_path:src/a.py", _INVALIDATION_CAUSE) in spy.invalidate_calls
    # workspace_snapshot:<prev_id> invalidated (prior snapshot generation)
    assert (
        f"workspace_snapshot:{prev_id}",
        _INVALIDATION_CAUSE,
    ) in spy.invalidate_calls
    # New snapshot id registered exactly once under the workspace_snapshot
    # TTL category.
    snapshot_puts = [
        c for c in spy.put_calls if c[0].startswith("workspace_snapshot:")
    ]
    assert snapshot_puts == [
        (f"workspace_snapshot:{new_id}", new_id, "workspace_snapshot")
    ]


def test_created_on_existing_path_raises(policy_cache: tuple) -> None:
    """CREATED on an already-tracked path raises and leaves state intact.

    Validates Requirement 3.2 — duplicate CREATED is a producer bug
    (the watcher should have emitted MODIFIED). The cache rejects
    the delta before any mutation or invalidation lands.
    """
    _, cache, spy = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    snapshot_after_first = cache.snapshot_id
    invalidate_count = len(spy.invalidate_calls)
    put_count = len(spy.put_calls)

    with pytest.raises(ValueError):
        cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))

    # State unchanged after the rejected second CREATED.
    assert cache.snapshot_id == snapshot_after_first
    assert cache.has_path("src/a.py") is True
    assert len(spy.invalidate_calls) == invalidate_count
    assert len(spy.put_calls) == put_count


def test_modified_updates_and_invalidates(policy_cache: tuple) -> None:
    """MODIFIED replaces metadata and invalidates both keys when content changes.

    Validates Requirement 3.2 — content-modify with new metadata
    invalidates the path key AND the prior snapshot id (because the
    snapshot composition changed).
    """
    _, cache, spy = policy_cache
    cache.apply_delta(
        _make_delta(type="CREATED", path="src/a.py", content_sha256=_HASH_A)
    )
    id_after_create = cache.snapshot_id
    spy.invalidate_calls.clear()
    spy.put_calls.clear()

    cache.apply_delta(
        _make_delta(
            type="MODIFIED",
            path="src/a.py",
            content_sha256=_HASH_B,
            mtime_ns=200,
            size=20,
        )
    )
    id_after_modify = cache.snapshot_id
    assert id_after_modify != id_after_create

    # workspace_path key invalidated
    assert ("workspace_path:src/a.py", _INVALIDATION_CAUSE) in spy.invalidate_calls
    # prior snapshot id invalidated
    assert (
        f"workspace_snapshot:{id_after_create}",
        _INVALIDATION_CAUSE,
    ) in spy.invalidate_calls
    # new snapshot id registered
    assert (
        f"workspace_snapshot:{id_after_modify}",
        id_after_modify,
        "workspace_snapshot",
    ) in spy.put_calls


def test_modified_idempotent_metadata_still_invalidates(
    policy_cache: tuple,
) -> None:
    """MODIFIED with byte-identical metadata still invalidates the path key.

    Validates Requirement 3.2 — Requirement 3.2's wording is
    unconditional ("WHEN a file is content-modified, THE policy
    SHALL invalidate"). The snapshot id does not change, but the
    path-key invalidation still fires.
    """
    _, cache, spy = policy_cache
    cache.apply_delta(
        _make_delta(
            type="CREATED",
            path="src/a.py",
            content_sha256=_HASH_A,
            mtime_ns=100,
            size=10,
        )
    )
    id_after_create = cache.snapshot_id
    spy.invalidate_calls.clear()
    spy.put_calls.clear()

    # Byte-identical metadata.
    cache.apply_delta(
        _make_delta(
            type="MODIFIED",
            path="src/a.py",
            content_sha256=_HASH_A,
            mtime_ns=100,
            size=10,
        )
    )

    # snapshot_id MUST be unchanged because the dict did not mutate.
    assert cache.snapshot_id == id_after_create
    # workspace_path key MUST still have been invalidated.
    assert spy.invalidate_calls == [
        ("workspace_path:src/a.py", _INVALIDATION_CAUSE)
    ]
    # No new put — snapshot generation did not move.
    assert spy.put_calls == []


def test_modified_missing_path_raises(policy_cache: tuple) -> None:
    """MODIFIED on a never-created path raises ``ValueError``.

    Validates Requirement 3.2 — MODIFIED on an untracked path is a
    producer bug (the watcher should have emitted CREATED).
    """
    _, cache, _ = policy_cache
    with pytest.raises(ValueError):
        cache.apply_delta(
            _make_delta(type="MODIFIED", path="src/nope.py", content_sha256=_HASH_A)
        )


def test_renamed_moves_and_invalidates_both_paths(policy_cache: tuple) -> None:
    """RENAMED drops old path, inserts new path, and invalidates both keys.

    Validates Requirement 3.2 — rename events invalidate the old
    AND the new path keys so any cached entry under either key is
    evicted.
    """
    _, cache, spy = policy_cache
    cache.apply_delta(
        _make_delta(type="CREATED", path="src/old.py", content_sha256=_HASH_A)
    )
    spy.invalidate_calls.clear()
    spy.put_calls.clear()

    cache.apply_delta(
        WorkspaceDelta(
            type="RENAMED",
            path="src/new.py",
            previous_path="src/old.py",
            mtime_ns=200,
            size=20,
            content_sha256=_HASH_B,
            detected_at_ns=3,
        )
    )

    assert cache.has_path("src/old.py") is False
    assert cache.has_path("src/new.py") is True

    invalidated_keys = {key for key, _ in spy.invalidate_calls}
    assert "workspace_path:src/old.py" in invalidated_keys
    assert "workspace_path:src/new.py" in invalidated_keys


def test_renamed_missing_previous_raises(policy_cache: tuple) -> None:
    """RENAMED with previous_path absent from the snapshot raises.

    Validates Requirement 3.2 — RENAMED requires the source key to
    be tracked; otherwise the cache cannot transfer metadata.
    """
    _, cache, _ = policy_cache
    with pytest.raises(ValueError):
        cache.apply_delta(
            WorkspaceDelta(
                type="RENAMED",
                path="src/new.py",
                previous_path="src/never_tracked.py",
                mtime_ns=200,
                size=20,
                content_sha256=_HASH_A,
                detected_at_ns=1,
            )
        )


def test_renamed_existing_target_raises(policy_cache: tuple) -> None:
    """RENAMED to an already-tracked target raises.

    Validates Requirement 3.2 — an unconditional overwrite would
    silently drop the target's metadata; the cache refuses.
    """
    _, cache, _ = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    cache.apply_delta(_make_delta(type="CREATED", path="src/b.py"))
    with pytest.raises(ValueError):
        cache.apply_delta(
            WorkspaceDelta(
                type="RENAMED",
                path="src/b.py",
                previous_path="src/a.py",
                mtime_ns=200,
                size=20,
                content_sha256=_HASH_B,
                detected_at_ns=1,
            )
        )


def test_renamed_pure_carries_previous_metadata(policy_cache: tuple) -> None:
    """Pure rename (content_sha256=None) carries the previous tuple verbatim.

    Validates Requirement 3.2 — when the watcher reports a rename
    without re-reading the body, the cache reuses the source
    metadata so the snapshot stays consistent.
    """
    _, cache, _ = policy_cache
    cache.apply_delta(
        _make_delta(
            type="CREATED",
            path="src/old.py",
            content_sha256=_HASH_A,
            mtime_ns=100,
            size=10,
        )
    )
    cache.apply_delta(
        WorkspaceDelta(
            type="RENAMED",
            path="src/new.py",
            previous_path="src/old.py",
            mtime_ns=999,  # ignored — pure rename carries previous tuple
            size=999,
            content_sha256=None,
            detected_at_ns=2,
        )
    )

    files = dict((path, (m, s, h)) for path, m, s, h in cache.files())
    assert "src/old.py" not in files
    assert files["src/new.py"] == (100, 10, _HASH_A)


def test_renamed_with_content_uses_delta_metadata(policy_cache: tuple) -> None:
    """RENAMED carrying a content hash trusts the delta metadata.

    Validates Requirement 3.2 — when the watcher reports both legs
    of the rename plus the post-rename body, the cache stores the
    new tuple verbatim.
    """
    _, cache, _ = policy_cache
    cache.apply_delta(
        _make_delta(
            type="CREATED",
            path="src/old.py",
            content_sha256=_HASH_A,
            mtime_ns=100,
            size=10,
        )
    )
    cache.apply_delta(
        WorkspaceDelta(
            type="RENAMED",
            path="src/new.py",
            previous_path="src/old.py",
            mtime_ns=200,
            size=20,
            content_sha256=_HASH_B,
            detected_at_ns=2,
        )
    )

    files = dict((path, (m, s, h)) for path, m, s, h in cache.files())
    assert files["src/new.py"] == (200, 20, _HASH_B)


def test_deleted_removes_and_invalidates(policy_cache: tuple) -> None:
    """DELETED removes the path and invalidates the path key.

    Validates Requirement 3.2 — deletion events evict any cached
    entry under the path's key.
    """
    _, cache, spy = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    spy.invalidate_calls.clear()
    spy.put_calls.clear()

    cache.apply_delta(_make_deleted(path="src/a.py"))

    assert cache.has_path("src/a.py") is False
    assert ("workspace_path:src/a.py", _INVALIDATION_CAUSE) in spy.invalidate_calls


def test_deleted_untracked_noop(policy_cache: tuple) -> None:
    """DELETED on an untracked path is a no-op.

    Validates Requirement 3.2 — a delete event for a file outside
    the snapshot's known set does NOT change snapshot_id and does
    NOT call ``policy.invalidate`` / ``policy.put``.
    """
    _, cache, spy = policy_cache
    snapshot_before = cache.snapshot_id
    invalidate_before = list(spy.invalidate_calls)
    put_before = list(spy.put_calls)

    cache.apply_delta(_make_deleted(path="src/never_tracked.py"))

    assert cache.snapshot_id == snapshot_before
    assert spy.invalidate_calls == invalidate_before
    assert spy.put_calls == put_before


def test_deleted_returns_to_empty_snapshot_constant(policy_cache: tuple) -> None:
    """CREATE then DELETE on the only path returns snapshot_id to the empty constant.

    Validates Requirement 3.2 — snapshot_id is a function of the
    current file set; emptying the set returns the canonical
    empty-snapshot hex.
    """
    _, cache, _ = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/only.py"))
    assert cache.snapshot_id != _EMPTY_SNAPSHOT_ID

    cache.apply_delta(_make_deleted(path="src/only.py"))
    assert cache.snapshot_id == _EMPTY_SNAPSHOT_ID
    assert cache.files() == ()


def test_snapshot_id_deterministic_insertion_order() -> None:
    """Two caches with the same final file set produce identical snapshot_ids.

    Validates Requirement 3.2 — the canonical serialization sorts
    by path, so insertion order does not affect the digest.
    """
    bus1 = EventBus(mission_id="m1")
    bus2 = EventBus(mission_id="m2")
    policy1 = CacheInvalidationPolicy(event_bus=bus1, clock=lambda: 0)
    policy2 = CacheInvalidationPolicy(event_bus=bus2, clock=lambda: 0)
    cache1 = WorkspaceSnapshotCache(invalidation_policy=policy1)
    cache2 = WorkspaceSnapshotCache(invalidation_policy=policy2)

    deltas_in_order_1 = [
        _make_delta(type="CREATED", path="src/a.py", content_sha256=_HASH_A, mtime_ns=10, size=1),
        _make_delta(type="CREATED", path="src/b.py", content_sha256=_HASH_B, mtime_ns=20, size=2),
        _make_delta(type="CREATED", path="src/c.py", content_sha256=_HASH_C, mtime_ns=30, size=3),
    ]
    deltas_in_order_2 = [
        _make_delta(type="CREATED", path="src/c.py", content_sha256=_HASH_C, mtime_ns=30, size=3),
        _make_delta(type="CREATED", path="src/a.py", content_sha256=_HASH_A, mtime_ns=10, size=1),
        _make_delta(type="CREATED", path="src/b.py", content_sha256=_HASH_B, mtime_ns=20, size=2),
    ]
    for delta in deltas_in_order_1:
        cache1.apply_delta(delta)
    for delta in deltas_in_order_2:
        cache2.apply_delta(delta)

    assert cache1.snapshot_id == cache2.snapshot_id


def test_path_normalization_windows_backslash(policy_cache: tuple) -> None:
    """Windows backslashes are normalized to forward slashes in keys and paths.

    Validates Requirement 3.2 — cross-platform deterministic key
    shapes; ``src\\foo.py`` and ``src/foo.py`` are the same logical
    path and produce the same ``workspace_path:src/foo.py`` key.
    """
    _, cache, spy = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src\\foo.py"))

    assert cache.has_path("src/foo.py") is True
    assert cache.has_path("src\\foo.py") is True  # normalization applies on lookup too
    invalidated_keys = {key for key, _ in spy.invalidate_calls}
    assert "workspace_path:src/foo.py" in invalidated_keys
    # The backslash form must NOT appear as a key.
    assert "workspace_path:src\\foo.py" not in invalidated_keys


# ===========================================================================
# Section D — TTL semantics (Requirement 3.4)
# ===========================================================================


def test_workspace_snapshot_ttl_300s_eviction(policy_cache: tuple) -> None:
    """``workspace_snapshot`` entries expire at 300 s (TTL upper bound).

    Validates Requirement 3.4 — the policy's TTL_NS for
    ``workspace_snapshot`` is 300 * 10**9 ns. After 301 s of clock
    advance, the registered snapshot id MUST be a cache miss.
    """
    policy, cache, spy = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    new_id = cache.snapshot_id
    key = f"workspace_snapshot:{new_id}"
    # Sanity: the policy holds the entry pre-TTL-expiry.
    assert policy.get(key) == new_id

    # Advance the policy clock by 301 seconds.
    spy.clock_holder["now_ns"] = 301 * 10**9
    assert policy.get(key) is None


def test_workspace_snapshot_within_ttl_returns_value(policy_cache: tuple) -> None:
    """``workspace_snapshot`` entries are live within the 300 s TTL window.

    Validates Requirement 3.4 — at 299 s of clock advance, the
    registered snapshot id is still readable.
    """
    policy, cache, spy = policy_cache
    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    new_id = cache.snapshot_id
    key = f"workspace_snapshot:{new_id}"

    spy.clock_holder["now_ns"] = 299 * 10**9
    assert policy.get(key) == new_id


def test_invalidate_explicit_evicts_workspace_path(policy_cache: tuple) -> None:
    """A child key registered under ``workspace_path:<p>`` is evicted on delete.

    Validates Requirement 3.4 — ``CacheInvalidationPolicy``'s
    dependency-graph traversal cascades from the path key to its
    registered children, so consumers that registered an
    ``evidence_selection`` entry as a dependent of a workspace path
    see a cache miss after the path is touched.
    """
    policy, cache, spy = policy_cache
    # Register the dep BEFORE the put so the put lands with the
    # dep-graph already wired.
    policy.register_dependency("workspace_path:src/a.py", "child_key")
    # Put the child entry directly via the spy-wrapped put. The spy
    # delegates to real_put so the entry actually lands in policy
    # state.
    policy.put("child_key", "child_value", ttl_category="evidence_selection")
    assert policy.get("child_key") == "child_value"

    cache.apply_delta(_make_delta(type="CREATED", path="src/a.py"))
    cache.apply_delta(_make_deleted(path="src/a.py"))

    # The CREATED + DELETED both invalidated workspace_path:src/a.py
    # which BFS-cascaded to child_key. The child entry is now a
    # cache miss.
    assert policy.get("child_key") is None


# ===========================================================================
# Section E — Event-type field round-trip (Requirement 3.2)
# ===========================================================================


@pytest.mark.parametrize(
    ("delta_type", "extra"),
    [
        (
            "CREATED",
            {"previous_path": None, "content_sha256": _HASH_A, "mtime_ns": 100, "size": 10},
        ),
        (
            "MODIFIED",
            {"previous_path": None, "content_sha256": _HASH_B, "mtime_ns": 200, "size": 20},
        ),
        (
            "RENAMED",
            {
                "previous_path": "src/old.py",
                "content_sha256": _HASH_C,
                "mtime_ns": 300,
                "size": 30,
            },
        ),
        (
            "DELETED",
            {"previous_path": None, "content_sha256": None, "mtime_ns": 0, "size": 0},
        ),
    ],
    ids=["CREATED", "MODIFIED", "RENAMED", "DELETED"],
)
def test_workspace_delta_event_type_field_round_trip(
    delta_type: str, extra: dict
) -> None:
    """All four ``type`` literals round-trip through JSON.

    Validates Requirement 3.2 — the watcher's emit-shape is a
    canonical JSON envelope; every type literal must survive a
    ``model_dump_json()`` / ``model_validate_json()`` round trip
    without mutation.
    """
    delta = WorkspaceDelta(
        type=delta_type,  # type: ignore[arg-type]
        path="src/x.py" if delta_type != "RENAMED" else "src/new.py",
        detected_at_ns=42,
        **extra,
    )
    payload = delta.model_dump_json()
    rehydrated = WorkspaceDelta.model_validate_json(payload)
    assert rehydrated == delta
    assert rehydrated.type == delta_type
