# Feature: sentinel-performance-runtime-foundation, Property 8: ArtifactRefStore SHA-256 round-trip, dedup, and integrity
"""Property-based test for ArtifactRefStore SHA-256 round-trip, dedup, integrity, and sanitization.

**Validates: Requirements 6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 6.8, 12.4**

Hypothesis strategies for bytes, text with embedded secret patterns, oversize
payloads, and corrupted on-disk blobs. Tests:
  - Round-trip: put then get returns identical bytes; ref has correct content_hash.
  - Dedup: same payload twice → same content_hash, only one file on disk.
  - Oversize rejected: payloads > 10 MB raise ValueError + ARTIFACT_REJECTED.
  - Sanitization rejects secrets: text payloads with secret patterns rejected
    when content_type='text' and llm_exposable=True.
  - Binary not scanned: binary payloads with secret patterns succeed.
  - Integrity error on corruption: corrupted on-disk file raises ArtifactIntegrityError.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.hot_cold.artifact_ref_store import (
    ArtifactIntegrityError,
    ArtifactRefStore,
)
from sentinel.shared.events import AgentEventType, EventBus


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Random bytes between 1 and 10000 bytes
_payload_st = st.binary(min_size=1, max_size=10000)

# Oversize payloads: 10*1024*1024 + 1 to 10*1024*1024 + 100
_oversize_offset_st = st.integers(min_value=1, max_value=100)

# Secret patterns that should trigger sanitization rejection.
# Many SECRET_PATTERNS use \b (word boundary), so the pattern must appear
# at a word boundary. We use a separator strategy that ensures the secret
# pattern is properly delimited (prefix ends with non-word char or is empty).
# AWS key pattern: AKIA + exactly 16 uppercase alphanumeric chars
# GitHub PAT: ghp_ + at least 20 alphanumeric chars
_secret_patterns_st = st.sampled_from([
    "password=abc123",
    "secret=mysecretvalue",
    "api_key=sk-abcdefghij1234567890",
    "AKIAIOSFODNN7EXAMPL0",  # AKIA + exactly 16 chars of [0-9A-Z]
    "ghp_ABCDEFGHIJKLMNOPQRSTU",  # ghp_ + 21 alphanumeric chars
    "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    "authorization: Bearer sk-abcdefghij1234567890",
    "client_secret=verysecretvalue123",
    "private_key=supersecretprivatekey",
    "passwd=hunter2",
])

# Separator characters that preserve word boundaries (non-word chars)
_separator_st = st.sampled_from(["", " ", "\n", "; ", ", ", ": ", "  ", "\t"])


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(payload=_payload_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_round_trip(payload: bytes) -> None:
    """Put then get returns identical bytes; ref has correct content_hash.

    **Validates: Requirements 6.1, 6.5**

    Generate random bytes (1–10000 bytes). `put` then `get` returns identical
    bytes. Ref has correct `content_hash` (verify independently with
    hashlib.sha256).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        ref = store.put(payload)

        # Verify content_hash matches independent SHA-256 computation
        expected_hash = hashlib.sha256(payload).hexdigest()
        assert ref.content_hash == expected_hash, (
            f"content_hash mismatch: {ref.content_hash} != {expected_hash}"
        )

        # Verify round-trip: get returns identical bytes
        retrieved = store.get(ref.content_hash)
        assert retrieved == payload, (
            f"Round-trip failed: retrieved {len(retrieved)} bytes != original {len(payload)} bytes"
        )


@given(payload=_payload_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_dedup(payload: bytes) -> None:
    """Put the same payload twice; second put returns same content_hash, only one file on disk.

    **Validates: Requirements 6.1, 6.2**

    Put the same payload twice. Second put returns a ref with the same
    `content_hash`. Only one file exists on disk.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        ref1 = store.put(payload)
        ref2 = store.put(payload)

        # Same content_hash
        assert ref1.content_hash == ref2.content_hash, (
            f"Dedup failed: {ref1.content_hash} != {ref2.content_hash}"
        )

        # Only one file on disk
        artifact_dir = Path(tmpdir) / "artifacts"
        all_files = list(artifact_dir.rglob("*"))
        # Filter to actual files (not directories)
        actual_files = [f for f in all_files if f.is_file()]
        assert len(actual_files) == 1, (
            f"Expected 1 file on disk, found {len(actual_files)}: {actual_files}"
        )


@given(offset=_oversize_offset_st)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_oversize_rejected(offset: int) -> None:
    """Oversize payloads raise ValueError and emit ARTIFACT_REJECTED with reason='size_overflow'.

    **Validates: Requirements 6.7**

    Generate payloads of size 10*1024*1024 + 1 to 10*1024*1024 + 100.
    Assert `put` raises `ValueError` and emits `ARTIFACT_REJECTED` with
    `reason="size_overflow"`.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        oversize_payload = b"\x00" * (10 * 1024 * 1024 + offset)

        events_before = len(event_bus.events())

        try:
            store.put(oversize_payload)
            raise AssertionError("Expected ValueError for oversize payload")
        except ValueError:
            pass

        # Check that ARTIFACT_REJECTED event was emitted
        events_after = event_bus.events()
        new_events = events_after[events_before:]
        rejected_events = [
            e for e in new_events
            if e.event_type == AgentEventType.ARTIFACT_REJECTED
        ]
        assert len(rejected_events) >= 1, (
            "Expected ARTIFACT_REJECTED event for oversize payload"
        )
        # Verify reason in payload
        assert rejected_events[0].payload.get("reason") == "size_overflow", (
            f"Expected reason='size_overflow', got {rejected_events[0].payload}"
        )


@given(secret_pattern=_secret_patterns_st, prefix=_separator_st, suffix=_separator_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_sanitization_rejects_secrets(
    secret_pattern: str, prefix: str, suffix: str
) -> None:
    """Text payloads with secret patterns rejected when content_type='text' and llm_exposable=True.

    **Validates: Requirements 12.4**

    Generate text payloads containing patterns that match SECRET_PATTERNS.
    Put with content_type='text', llm_exposable=True. Assert raises ValueError
    and emits ARTIFACT_REJECTED with reason='secret_pattern_detected'.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        text_with_secret = f"{prefix}{secret_pattern}{suffix}"
        payload = text_with_secret.encode("utf-8")

        events_before = len(event_bus.events())

        try:
            store.put(payload, content_type="text", llm_exposable=True)
            raise AssertionError(
                f"Expected ValueError for secret pattern: {secret_pattern!r}"
            )
        except ValueError:
            pass

        # Check that ARTIFACT_REJECTED event was emitted
        events_after = event_bus.events()
        new_events = events_after[events_before:]
        rejected_events = [
            e for e in new_events
            if e.event_type == AgentEventType.ARTIFACT_REJECTED
        ]
        assert len(rejected_events) >= 1, (
            "Expected ARTIFACT_REJECTED event for secret pattern"
        )
        assert rejected_events[0].payload.get("reason") == "secret_pattern_detected", (
            f"Expected reason='secret_pattern_detected', got {rejected_events[0].payload}"
        )


@given(secret_pattern=_secret_patterns_st, prefix=_separator_st, suffix=_separator_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_binary_not_scanned(
    secret_pattern: str, prefix: str, suffix: str
) -> None:
    """Binary payloads with secret patterns succeed (no rejection).

    **Validates: Requirements 6.1, 12.4**

    Same secret-containing bytes but content_type='binary'. Assert `put`
    succeeds (no rejection).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        text_with_secret = f"{prefix}{secret_pattern}{suffix}"
        payload = text_with_secret.encode("utf-8")

        # Binary content_type should NOT trigger sanitization
        ref = store.put(payload, content_type="binary", llm_exposable=False)

        # Verify it succeeded
        assert ref is not None, "Expected successful put for binary payload"
        assert ref.content_hash == hashlib.sha256(payload).hexdigest()

        # Also test binary with llm_exposable=True — still no scan
        with tempfile.TemporaryDirectory() as tmpdir2:
            event_bus2 = EventBus(mission_id="mission_artifact_test2")
            store2 = ArtifactRefStore(tmpdir2, event_bus=event_bus2)

            ref2 = store2.put(payload, content_type="binary", llm_exposable=True)
            assert ref2 is not None, "Expected successful put for binary+llm_exposable payload"


@given(payload=_payload_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_integrity_error_on_corruption(payload: bytes) -> None:
    """Corrupted on-disk file raises ArtifactIntegrityError and emits ARTIFACT_INTEGRITY_ERROR.

    **Validates: Requirements 6.5, 6.6**

    Put a payload, then corrupt the on-disk file (flip a byte). `get` should
    raise `ArtifactIntegrityError` and emit `ARTIFACT_INTEGRITY_ERROR`.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        event_bus = EventBus(mission_id="mission_artifact_test")
        store = ArtifactRefStore(tmpdir, event_bus=event_bus)

        ref = store.put(payload)

        # Locate the on-disk file and corrupt it
        content_hash = ref.content_hash
        prefix = content_hash[:2]
        artifact_path = Path(tmpdir) / "artifacts" / prefix / content_hash

        assert artifact_path.exists(), f"Artifact file not found at {artifact_path}"

        # Read the file, flip a byte, write it back
        data = artifact_path.read_bytes()
        corrupted = bytearray(data)
        # Flip the first byte
        corrupted[0] = (corrupted[0] + 1) % 256
        artifact_path.write_bytes(bytes(corrupted))

        events_before = len(event_bus.events())

        # get should raise ArtifactIntegrityError
        try:
            store.get(content_hash)
            raise AssertionError(
                "Expected ArtifactIntegrityError for corrupted artifact"
            )
        except ArtifactIntegrityError:
            pass

        # Check that ARTIFACT_INTEGRITY_ERROR event was emitted
        events_after = event_bus.events()
        new_events = events_after[events_before:]
        integrity_events = [
            e for e in new_events
            if e.event_type == AgentEventType.ARTIFACT_INTEGRITY_ERROR
        ]
        assert len(integrity_events) >= 1, (
            "Expected ARTIFACT_INTEGRITY_ERROR event for corrupted artifact"
        )
