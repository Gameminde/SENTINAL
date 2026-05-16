from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from sentinel.agent.context_engine import ContextNeed
from sentinel.agent.receipt_retriever import ReceiptRecord
from sentinel.agent.token_ledger import estimate_tokens
from sentinel.shared.models import SentinelModel, new_id


SECRET_PATTERNS = [
    # Task 9 / F-A2.1 — explicit coverage for each documented secret
    # shape. The patterns run in order; earlier matches do not prevent
    # later ones from firing on separate occurrences of the same
    # string, so multi-secret lines are fully redacted.
    #
    # OpenAI / Stripe sk-/sk_ style.
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{10,}"),
    # AWS access-key id (AKIA / ASIA / AROA / AIDA / ANPA / ANVA / ACCA).
    re.compile(r"\b(?:AKIA|ASIA|AROA|AIDA|ANPA|ANVA|ACCA)[0-9A-Z]{16}\b"),
    # GitHub personal access tokens (classic + fine-grained) and OAuth
    # / app tokens.
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    # Google API keys — exactly 39 chars total: "AIza" + 35 of
    # ``[0-9A-Za-z_-]``. The body alphabet includes ``-`` and ``_``
    # which have asymmetric ``\b`` semantics (``-`` is ``\W`` so a
    # trailing ``\b`` after a ``-`` does not form a word boundary and
    # the match fails). We use explicit lookahead/lookbehind class
    # negation to anchor the key without relying on ``\b``.
    re.compile(r"(?<![0-9A-Za-z_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])"),
    # Slack tokens. Same ``-``-in-class issue as Google keys; use
    # class-negation lookarounds for the trailing boundary.
    re.compile(r"(?<![A-Za-z0-9-])xox[abprs]-[A-Za-z0-9-]{10,}(?![A-Za-z0-9-])"),
    # JWT — three base64url segments separated by dots. Tighter than
    # generic base64 so it does not eat ordinary dotted identifiers.
    # Using class-negation lookarounds: the trailing segment may end
    # with ``-`` (``\W`` under Python's default word-char class),
    # which breaks a naive trailing ``\b``.
    re.compile(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}(?![A-Za-z0-9_-])"
    ),
    # PEM private key blocks. DOTALL so the body between BEGIN/END is
    # swallowed wholesale.
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r"[\s\S]+?"
        r"-----END [A-Z ]*PRIVATE KEY-----"
    ),
    # Database connection strings with inline credentials. Match the
    # credential segment after the scheme; the scheme and host tail
    # are preserved through the replacement token so context about
    # "postgres URL was here" is not lost.
    re.compile(
        r"(?P<scheme>(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?"
        r"|redis|amqp|amqps|ftp|ftps|sftp|ssh|rediss))"
        r"://[^\s:/@]+:[^\s@]+@"
    ),
    # Authorization / Bearer headers.
    re.compile(r"(?i)\bauthorization\s*[:=]\s*(?:bearer\s+)?\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{10,}"),
    # Generic `name=value` style. The alternation also covers
    # ``access_token``, ``auth_token``, ``refresh_token``,
    # ``client_secret``, ``private_key``, etc. Matches both ``=`` and
    # ``:`` separators and supports optional quoting around the value.
    re.compile(
        r"(?i)\b("
        r"api[_-]?key"
        r"|access[_-]?token"
        r"|auth[_-]?token"
        r"|refresh[_-]?token"
        r"|client[_-]?secret"
        r"|private[_-]?key"
        r"|token"
        r"|secret"
        r"|password"
        r"|passwd"
        r"|pwd"
        r")\s*[:=]\s*\"?[^\s\"',;]+\"?"
    ),
]


def sanitize_context_text(text: str) -> str:
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def sanitize_context_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return sanitize_context_text(payload)
    if isinstance(payload, list):
        return [sanitize_context_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(sanitize_context_payload(item) for item in payload)
    if isinstance(payload, dict):
        return {sanitize_context_payload(key): sanitize_context_payload(value) for key, value in payload.items()}
    return payload


class EvidenceCard(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("evcard"))
    receipt_id: str
    source_type: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0)
    token_count: int = Field(ge=0)
    critical: bool = False


class EvidenceRanker:
    """Turns selected receipts into compact evidence cards."""

    def rank(self, receipts: list[ReceiptRecord], need: ContextNeed) -> list[EvidenceCard]:
        cards = [self._card(receipt, need) for receipt in receipts]
        return sorted(cards, key=lambda card: (-card.relevance_score, card.receipt_id))

    @staticmethod
    def _card(receipt: ReceiptRecord, need: ContextNeed) -> EvidenceCard:
        required_bonus = 2.0 if set(receipt.evidence_refs) & set(need.required_evidence_refs) else 0.0
        critical_bonus = 1.0 if receipt.critical else 0.0
        tag_bonus = len(set(receipt.relevance_tags) & set(need.keywords)) * 0.5
        summary = sanitize_context_text(receipt.summary)
        return EvidenceCard(
            receipt_id=receipt.receipt_id,
            source_type=receipt.source_type,
            summary=summary,
            evidence_refs=receipt.evidence_refs,
            relevance_score=round(1.0 + required_bonus + critical_bonus + tag_bonus, 6),
            token_count=estimate_tokens(summary),
            critical=receipt.critical,
        )
