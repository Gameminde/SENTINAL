"""Content-addressed artifact store keyed by SHA-256.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 12.4

Sanitization policy:
    Binary payloads are NEVER regex-scanned. The sanitization gate fires
    only when content_type='text' AND llm_exposable=True. In that case,
    the canonical ``sanitize_context_text`` is applied; if the sanitized
    output differs from the original, the artifact is rejected with an
    ARTIFACT_REJECTED event.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ConfigDict

from sentinel.agent.evidence_ranker import sanitize_context_text
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


class ArtifactRef(SentinelModel):
    """Frozen reference to a stored artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content_hash: str
    size_bytes: int
    content_type: str
    llm_exposable: bool
    created_at: datetime


class ArtifactIntegrityError(Exception):
    """Raised when a read artifact's recomputed SHA-256 does not match its key."""


class ArtifactRefStore:
    """Content-addressed store, keyed by SHA-256. Deduplicates on put.

    On-disk layout: ``<root>/artifacts/<sha256[0:2]>/<sha256>``
    """

    MAX_ARTIFACT_BYTES: int = 10 * 1024 * 1024  # 10 MB

    def __init__(self, root: Path | str, *, event_bus: EventBus) -> None:
        self._root = Path(root) / "artifacts"
        self._root.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus

    def _artifact_path(self, content_hash: str) -> Path:
        """Compute the on-disk path for a given content hash."""
        prefix = content_hash[:2]
        return self._root / prefix / content_hash

    def put(
        self,
        payload: bytes,
        *,
        content_type: str = "binary",
        llm_exposable: bool = False,
    ) -> ArtifactRef:
        """Store an artifact by its SHA-256 content hash.

        - Rejects payloads > 10 MB with ARTIFACT_REJECTED event + ValueError.
        - Deduplicates: if the hash already exists on disk, returns existing ref.
        - Sanitization gate: when content_type='text' AND llm_exposable=True,
          decodes as UTF-8 and runs sanitize_context_text; rejects if secrets
          are detected.
        - Atomic write via tmp + os.replace; cleans up on OSError.
        """
        # --- Size check ---
        if len(payload) > self.MAX_ARTIFACT_BYTES:
            self._event_bus.append(
                event_type=AgentEventType.ARTIFACT_REJECTED,
                summary="Artifact rejected: size overflow",
                payload={"reason": "size_overflow", "size": len(payload)},
            )
            raise ValueError("Artifact exceeds 10 MB cap")

        # --- Compute content hash ---
        content_hash = hashlib.sha256(payload).hexdigest()

        # --- Dedup check ---
        artifact_path = self._artifact_path(content_hash)
        if artifact_path.exists():
            # Return existing ref without re-writing
            return ArtifactRef(
                content_hash=content_hash,
                size_bytes=len(payload),
                content_type=content_type,
                llm_exposable=llm_exposable,
                created_at=datetime.now(UTC),
            )

        # --- Sanitization gate (text + llm_exposable only) ---
        if content_type == "text" and llm_exposable:
            decoded = payload.decode("utf-8")
            sanitized = sanitize_context_text(decoded)
            if sanitized != decoded:
                self._event_bus.append(
                    event_type=AgentEventType.ARTIFACT_REJECTED,
                    summary="Artifact rejected: secret pattern detected",
                    payload={
                        "reason": "secret_pattern_detected",
                        "content_hash": content_hash,
                    },
                )
                raise ValueError("Artifact rejected: secret pattern detected")

        # --- Write atomically ---
        prefix_dir = artifact_path.parent
        prefix_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = artifact_path.with_suffix(".tmp")

        try:
            tmp_path.write_bytes(payload)
            os.replace(str(tmp_path), str(artifact_path))
        except OSError:
            # Clean up partial file
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._event_bus.append(
                event_type=AgentEventType.ARTIFACT_REJECTED,
                summary="Artifact rejected: storage exhaustion",
                payload={"reason": "storage_exhaustion"},
            )
            raise

        return ArtifactRef(
            content_hash=content_hash,
            size_bytes=len(payload),
            content_type=content_type,
            llm_exposable=llm_exposable,
            created_at=datetime.now(UTC),
        )

    def get(self, content_hash: str) -> bytes:
        """Retrieve an artifact by content hash with integrity verification.

        Recomputes SHA-256 on read; raises ArtifactIntegrityError on mismatch.
        Raises KeyError if the artifact does not exist.
        """
        artifact_path = self._artifact_path(content_hash)
        if not artifact_path.exists():
            raise KeyError(f"artifact {content_hash} not found")

        data = artifact_path.read_bytes()

        # --- Integrity check ---
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != content_hash:
            self._event_bus.append(
                event_type=AgentEventType.ARTIFACT_INTEGRITY_ERROR,
                summary=f"Integrity check failed for {content_hash}",
                payload={
                    "content_hash": content_hash,
                    "actual_hash": actual_hash,
                },
            )
            raise ArtifactIntegrityError(
                f"Integrity check failed for {content_hash}"
            )

        return data


__all__ = [
    "ArtifactIntegrityError",
    "ArtifactRef",
    "ArtifactRefStore",
]
