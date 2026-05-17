"""ContextCacheKey data shapes and exceptions for sentinel-context-cache-runtime-closure.

Spec: ``sentinel-context-cache-runtime-closure``.
Closure backlog items: P-C-KEY-01 / P-C-RUNTIME-01.
Foundation-lock anchor commit: ``378d862310bc1b5939b210a49c04026cd99a860d``
(``perf: fully lock benchmark regression gates``).

This module is pure: no I/O, no EventBus emission, no module-level mutable
state, no mutation of caller-owned objects.

Task 2.1 introduces ONLY the data shapes, exceptions, and module constants.
The ``ContextCacheKeyBuilder`` class is deferred to Task 2.2.

Public surface introduced by this task
--------------------------------------
- :class:`ContextCacheKey` — Pydantic v2 frozen model holding the four
  component SHA-256 hex hashes plus the composite SHA-256 hex hash that
  together identify a cache entry under
  ``sentinel-performance-runtime-foundation`` Phase C semantics.
- :class:`OrganStateView` / :class:`OrganStateEntry` — read-only Pydantic v2
  input containers for the organ-state-hash component. Sorted-list
  invariants are enforced at construction time so the (later) builder can
  rely on a deterministic canonical form.
- :class:`MissingCacheKeyComponent` — exception raised by the builder
  (Task 2.2) when an input component is missing or unresolved.
- :class:`CacheKeySanitizerRejection` — exception raised by the builder
  (Task 2.2) when a string-typed input contains material rejected by the
  canonical sanitizer.

The module-level constants (``_FIELD_SEPARATOR``, ``_RECORD_SEPARATOR``,
``_VOLATILE_FIELDS``) are deliberately private (underscore-prefixed). They
are consumed by the Task 2.2 builder; tests may import them via the
fully-qualified module path.

Imports are kept to the minimum required by the data shapes alone; in
particular this module does NOT import ``EventBus``, ``AgentEventType``,
``MissionAuthorityEnvelope``, ``AgentContext``, ``OrganKillSwitch``, the
canonical sanitizer, or any other cache helper under
``sentinel.perf.caches``. Those are exclusively the concern of Task 2.2.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ConfigDict, field_validator

from sentinel.agent.evidence_ranker import sanitize_context_text
from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# Module-level constants (consumed by Task 2.2 ContextCacheKeyBuilder)
# ---------------------------------------------------------------------------

# ASCII Unit Separator. Cannot appear in the lowercase hex output of any
# component hash, so component values cannot collide with the separator
# itself.
_FIELD_SEPARATOR: bytes = b"\x1f"

# ASCII Record Separator. Reserved for future composite shapes; not used
# by the four-component composite defined in design.md.
_RECORD_SEPARATOR: bytes = b"\x1e"

# Volatile / non-functional field names excluded from canonical-form
# hashing. Implementations of the Task 2.2 builder strip these fields
# before computing SHA-256 over any model dump. This list is append-only
# across waves; new exclusions must be justified in the same commit that
# adds them.
_VOLATILE_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "ended_at",
        "expires_at",
        "trace_id",
        "trace_refs",
        "ts_ns",
        "logical_time",
        "sequence",
        "previous_hash",
        "event_hash",
        "receipt_hash",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_HEX_ALPHABET: frozenset[str] = frozenset("0123456789abcdef")


def _validate_lowercase_hex64(value: str, field_name: str) -> str:
    """Return ``value`` unchanged when it is a 64-character lowercase hex
    string; raise ``ValueError`` otherwise.

    The check is deliberately strict: exactly 64 characters, every
    character drawn from ``0123456789abcdef``. Uppercase is rejected so
    that two callers that compute the same SHA-256 cannot disagree on
    casing.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a 64-character lowercase hex string"
        )
    if len(value) != 64 or not all(c in _HEX_ALPHABET for c in value):
        raise ValueError(
            f"{field_name} must be a 64-character lowercase hex string"
        )
    return value


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


class ContextCacheKey(SentinelModel):
    """Four-component cache key plus its composite hash.

    Frozen Pydantic v2 model. Holds only SHA-256 hex digests — never raw
    inputs, payloads, or substrings of inputs. ``extra="forbid"`` rejects
    unknown fields so callers cannot smuggle volatile state through the
    key.

    Requirements: 1.1, 1.4, 1.6, 5.2.
    """

    mission_hot_hash: str
    workspace_snapshot_id: str
    organ_state_hash: str
    authority_hash: str
    composite_hash: str

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator(
        "mission_hot_hash",
        "workspace_snapshot_id",
        "organ_state_hash",
        "authority_hash",
        "composite_hash",
    )
    @classmethod
    def _validate_hex64(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        return _validate_lowercase_hex64(value, info.field_name)


class OrganStateEntry(SentinelModel):
    """Read-only view over a single organ's state for hashing.

    Fields are exactly the inputs that affect ``organ_state_hash`` per
    design.md §Hash Derivation for Each Component. ``advertised_capabilities``
    must be sorted ascending and deduplicated so the canonical form is
    deterministic.
    """

    organ_id: str
    execution_allowed: bool
    advertised_capabilities: list[str]
    kill_switch_triggered: bool

    model_config = ConfigDict(extra="forbid")

    @field_validator("organ_id")
    @classmethod
    def _validate_organ_id(cls, value: str) -> str:
        if not value:
            raise ValueError("organ_id must be non-empty")
        return value

    @field_validator("advertised_capabilities")
    @classmethod
    def _validate_capabilities(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError(
                "advertised_capabilities must be sorted ascending and deduplicated"
            )
        return value


class OrganStateView(SentinelModel):
    """Read-only collection of :class:`OrganStateEntry` for hashing.

    ``organs`` MUST be sorted ascending by ``organ_id`` so the (later)
    builder can produce a deterministic canonical form without a sort
    pass. The view is NOT frozen — it is an input container, constructed
    once per cache-key derivation by the caller and discarded.
    """

    organs: list[OrganStateEntry]

    model_config = ConfigDict(extra="forbid")

    @field_validator("organs")
    @classmethod
    def _validate_sorted(cls, value: list[OrganStateEntry]) -> list[OrganStateEntry]:
        ids = [entry.organ_id for entry in value]
        if ids != sorted(ids):
            raise ValueError("organs must be sorted ascending by organ_id")
        return value


# ---------------------------------------------------------------------------
# Exceptions (consumed by the Task 2.2 builder)
# ---------------------------------------------------------------------------


class MissingCacheKeyComponent(ValueError):
    """Raised by ``ContextCacheKeyBuilder.derive`` (Task 2.2) when any of
    ``envelope``, ``context``, ``organ_state``, ``workspace_snapshot_id``,
    or ``original_allowed_actions`` is ``None`` / empty / unresolved at
    the call site. Never falls back to ``envelope.id``,
    ``envelope.original_allowed_actions``, or any partial key.
    """

    pass


class CacheKeySanitizerRejection(ValueError):
    """Raised by ``ContextCacheKeyBuilder.derive`` (Task 2.2) when any
    string-typed input field contains SecretMaterial as detected by the
    canonical ``sanitize_context_text`` / ``sanitize_context_payload``
    gate. The exception message MUST NOT echo the rejected substring.
    """

    pass


# ---------------------------------------------------------------------------
# ContextCacheKeyBuilder (Task 2.2)
# ---------------------------------------------------------------------------


class ContextCacheKeyBuilder:
    """Pure staticmethod namespace that derives :class:`ContextCacheKey`.

    Strategy A (preferred): all methods are ``@staticmethod``. No instance
    state. No I/O. No EventBus emission. No mutation of caller-owned
    objects. No module-level mutable state.

    The four-component cache key is the canonical SHA-256 hex digest over
    a deterministic JSON canonicalisation of the inputs (sorted keys,
    no whitespace, ASCII-safe). The composite hash is SHA-256 over the
    concatenation of the four component hex digests separated by
    ``_FIELD_SEPARATOR``.

    The ``original_allowed_actions`` argument is REQUIRED EXPLICITLY on
    both ``derive(...)`` and ``authority_hash(...)``. There is no
    fallback to ``envelope.original_allowed_actions`` (which does not
    exist) or to ``envelope.id``. Missing or ``None`` raises
    :class:`MissingCacheKeyComponent`.

    Every string-typed input included in any canonical form is passed
    through the canonical ``sanitize_context_text`` gate. If the
    sanitizer modifies the value (i.e., the input contained
    SecretMaterial), the builder raises :class:`CacheKeySanitizerRejection`
    and never produces a key. The exception message MUST NOT echo the
    raw value, the rejected substring, or any payload byte.

    Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10, 2.1, 2.2,
    2.3, 2.4, 2.5, 5.1, 5.2, 5.6, 10.1, 10.6.
    """

    # --- helpers (private, staticmethod) ---

    @staticmethod
    def _canonical_json_bytes(value: Any) -> bytes:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    @staticmethod
    def _sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _check_clean(value: str, *, field_name: str) -> str:
        # Sanitizer is substitution-based: if the sanitized output differs,
        # the input contained SecretMaterial. Raise WITHOUT echoing the raw
        # value or any substring of it.
        if not isinstance(value, str):
            raise CacheKeySanitizerRejection(
                f"{field_name} must be a string before sanitization"
            )
        sanitized = sanitize_context_text(value)
        if sanitized != value:
            raise CacheKeySanitizerRejection(
                f"{field_name} contained material rejected by the canonical sanitizer"
            )
        return value

    @staticmethod
    def _normalize_enum_or_str(value: Any, *, field_name: str) -> str:
        if value is None:
            raise MissingCacheKeyComponent(f"{field_name} is required")
        # StrEnum / Enum / plain str — pull the .value if available, else stringify.
        token = value.value if hasattr(value, "value") else value
        token = str(token)
        return ContextCacheKeyBuilder._check_clean(token, field_name=field_name)

    @staticmethod
    def _sanitized_sorted_unique_strs(values: Any, *, field_name: str) -> list[str]:
        # Accept list/tuple/None. Treat None or missing as []. Sanitize every
        # string; sort + dedupe (preserving sort-after-dedupe canonical form).
        if values is None:
            return []
        if isinstance(values, (list, tuple)):
            seen: set[str] = set()
            out: list[str] = []
            for item in values:
                if not isinstance(item, str):
                    raise CacheKeySanitizerRejection(
                        f"{field_name} entries must be strings before sanitization"
                    )
                ContextCacheKeyBuilder._check_clean(item, field_name=field_name)
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return sorted(out)
        raise CacheKeySanitizerRejection(
            f"{field_name} must be a list or tuple of strings"
        )

    # --- component hashes ---

    @staticmethod
    def mission_hot_hash(envelope: Any, context: Any) -> str:
        if envelope is None:
            raise MissingCacheKeyComponent("envelope is required for mission_hot_hash")
        if context is None:
            raise MissingCacheKeyComponent("context is required for mission_hot_hash")
        # Required core inputs from envelope.
        mission_objective_raw = getattr(envelope, "mission_objective", None)
        if mission_objective_raw is None:
            raise MissingCacheKeyComponent("envelope.mission_objective is required")
        mission_type_raw = getattr(envelope, "mission_type", None)
        if mission_type_raw is None:
            raise MissingCacheKeyComponent("envelope.mission_type is required")
        success_criteria_raw = getattr(envelope, "success_criteria", None)
        # Required core inputs from context.
        constraints_raw = getattr(context, "constraints", None)
        evidence_refs_raw = getattr(context, "evidence_refs", None)
        # Optional: blockers may not be present on this AgentContext shape.
        blockers_raw = getattr(context, "blockers", None)

        canonical_form = {
            "mission_objective": ContextCacheKeyBuilder._check_clean(
                str(mission_objective_raw), field_name="mission_objective"
            ),
            "mission_type": ContextCacheKeyBuilder._normalize_enum_or_str(
                mission_type_raw, field_name="mission_type"
            ),
            "success_criteria": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                success_criteria_raw, field_name="success_criteria"
            ),
            "constraints": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                constraints_raw, field_name="constraints"
            ),
            "blockers": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                blockers_raw, field_name="blockers"
            ),
            "evidence_refs": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                evidence_refs_raw, field_name="evidence_refs"
            ),
        }
        return ContextCacheKeyBuilder._sha256_hex(
            ContextCacheKeyBuilder._canonical_json_bytes(canonical_form)
        )

    @staticmethod
    def organ_state_hash(organ_state: Any) -> str:
        if organ_state is None:
            raise MissingCacheKeyComponent("organ_state is required for organ_state_hash")
        organs_raw = getattr(organ_state, "organs", None)
        if organs_raw is None:
            raise MissingCacheKeyComponent("organ_state.organs is required")
        # The Pydantic OrganStateView validator already enforces ascending
        # organ_id order and OrganStateEntry validators enforce sorted+
        # deduped advertised_capabilities and non-empty organ_id. Re-check
        # nothing; serialize directly.
        canonical_form = {
            "organs": [
                {
                    "organ_id": ContextCacheKeyBuilder._check_clean(
                        str(getattr(entry, "organ_id")), field_name="organ_id"
                    ),
                    "execution_allowed": bool(getattr(entry, "execution_allowed")),
                    "advertised_capabilities": [
                        ContextCacheKeyBuilder._check_clean(
                            str(cap), field_name="advertised_capabilities"
                        )
                        for cap in getattr(entry, "advertised_capabilities", []) or []
                    ],
                    "kill_switch_triggered": bool(getattr(entry, "kill_switch_triggered")),
                }
                for entry in organs_raw
            ],
        }
        return ContextCacheKeyBuilder._sha256_hex(
            ContextCacheKeyBuilder._canonical_json_bytes(canonical_form)
        )

    @staticmethod
    def authority_hash(
        envelope: Any,
        *,
        original_allowed_actions: tuple[str, ...] | list[str],
    ) -> str:
        if envelope is None:
            raise MissingCacheKeyComponent("envelope is required for authority_hash")
        if original_allowed_actions is None:
            raise MissingCacheKeyComponent(
                "original_allowed_actions is required for authority_hash (no fallback)"
            )
        if not isinstance(original_allowed_actions, (tuple, list)):
            raise MissingCacheKeyComponent(
                "original_allowed_actions must be a tuple or list of strings"
            )
        # Required authority-relevant fields.
        mission_type_raw = getattr(envelope, "mission_type", None)
        if mission_type_raw is None:
            raise MissingCacheKeyComponent("envelope.mission_type is required")
        allowed_actions_raw = getattr(envelope, "allowed_actions", None)
        allowed_tools_raw = getattr(envelope, "allowed_tools", None)
        max_actions_raw = getattr(envelope, "max_actions", None)
        if max_actions_raw is None:
            raise MissingCacheKeyComponent("envelope.max_actions is required")
        max_cost_usd_raw = getattr(envelope, "max_cost_usd", None)
        if max_cost_usd_raw is None:
            raise MissingCacheKeyComponent("envelope.max_cost_usd is required")
        mode_raw = getattr(envelope, "mode", None)
        if mode_raw is None:
            raise MissingCacheKeyComponent("envelope.mode is required")
        expires_at_raw = getattr(envelope, "expires_at", None)
        revoked_at_raw = getattr(envelope, "revoked_at", None)

        canonical_form = {
            "mission_type": ContextCacheKeyBuilder._normalize_enum_or_str(
                mission_type_raw, field_name="mission_type"
            ),
            "allowed_actions": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                allowed_actions_raw, field_name="allowed_actions"
            ),
            "allowed_tools": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                allowed_tools_raw, field_name="allowed_tools"
            ),
            "max_actions": int(max_actions_raw),
            "max_cost_usd": format(float(max_cost_usd_raw), ".6f"),
            "mode": ContextCacheKeyBuilder._normalize_enum_or_str(
                mode_raw, field_name="mode"
            ),
            "expires_at": (
                expires_at_raw.isoformat() if hasattr(expires_at_raw, "isoformat")
                else (None if expires_at_raw is None else str(expires_at_raw))
            ),
            "revoked_at": (
                revoked_at_raw.isoformat() if hasattr(revoked_at_raw, "isoformat")
                else (None if revoked_at_raw is None else str(revoked_at_raw))
            ),
            "original_allowed_actions": ContextCacheKeyBuilder._sanitized_sorted_unique_strs(
                list(original_allowed_actions),
                field_name="original_allowed_actions",
            ),
        }
        return ContextCacheKeyBuilder._sha256_hex(
            ContextCacheKeyBuilder._canonical_json_bytes(canonical_form)
        )

    # --- composite ---

    @staticmethod
    def _composite(
        *,
        mission_hot_hash: str,
        workspace_snapshot_id: str,
        organ_state_hash: str,
        authority_hash: str,
    ) -> str:
        # SHA-256 of canonical concat in fixed order with _FIELD_SEPARATOR
        # between each pair. _FIELD_SEPARATOR (0x1f) cannot appear in a
        # lowercase-hex SHA-256 output, so the four components are
        # unambiguously parseable.
        joined = (
            mission_hot_hash.encode("ascii")
            + _FIELD_SEPARATOR
            + workspace_snapshot_id.encode("ascii")
            + _FIELD_SEPARATOR
            + organ_state_hash.encode("ascii")
            + _FIELD_SEPARATOR
            + authority_hash.encode("ascii")
        )
        return ContextCacheKeyBuilder._sha256_hex(joined)

    # --- top-level entry point ---

    @staticmethod
    def derive(
        *,
        envelope: Any,
        context: Any,
        organ_state: Any,
        workspace_snapshot_id: str,
        original_allowed_actions: tuple[str, ...] | list[str],
    ) -> ContextCacheKey:
        # Required-input gating. NEVER fall back to envelope.id, to
        # envelope.original_allowed_actions, or to any partial key.
        if envelope is None:
            raise MissingCacheKeyComponent("envelope is required")
        if context is None:
            raise MissingCacheKeyComponent("context is required")
        if organ_state is None:
            raise MissingCacheKeyComponent("organ_state is required")
        if workspace_snapshot_id is None or workspace_snapshot_id == "":
            raise MissingCacheKeyComponent(
                "workspace_snapshot_id is required (non-empty string)"
            )
        if not isinstance(workspace_snapshot_id, str):
            raise MissingCacheKeyComponent(
                "workspace_snapshot_id must be a string"
            )
        if original_allowed_actions is None:
            raise MissingCacheKeyComponent(
                "original_allowed_actions is required (no fallback)"
            )
        if not isinstance(original_allowed_actions, (tuple, list)):
            raise MissingCacheKeyComponent(
                "original_allowed_actions must be a tuple or list of strings"
            )

        # Compute four component hashes. Each helper applies the canonical
        # sanitizer and raises CacheKeySanitizerRejection on any
        # SecretMaterial detection.
        m_hash = ContextCacheKeyBuilder.mission_hot_hash(envelope, context)
        o_hash = ContextCacheKeyBuilder.organ_state_hash(organ_state)
        a_hash = ContextCacheKeyBuilder.authority_hash(
            envelope, original_allowed_actions=original_allowed_actions
        )
        # workspace_snapshot_id is consumed verbatim per design — must be
        # a 64-char lowercase hex string per the Phase E lock; the
        # ContextCacheKey field validator enforces this when the model is
        # constructed below, so a bad value surfaces as ValidationError
        # there rather than here.
        w_hash = workspace_snapshot_id

        c_hash = ContextCacheKeyBuilder._composite(
            mission_hot_hash=m_hash,
            workspace_snapshot_id=w_hash,
            organ_state_hash=o_hash,
            authority_hash=a_hash,
        )
        return ContextCacheKey(
            mission_hot_hash=m_hash,
            workspace_snapshot_id=w_hash,
            organ_state_hash=o_hash,
            authority_hash=a_hash,
            composite_hash=c_hash,
        )


__all__ = [
    "ContextCacheKey",
    "OrganStateView",
    "OrganStateEntry",
    "MissingCacheKeyComponent",
    "CacheKeySanitizerRejection",
    "ContextCacheKeyBuilder",
]
