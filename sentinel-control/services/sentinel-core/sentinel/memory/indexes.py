from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from sentinel.memory.models import MemoryRecord, MemoryTrustClass


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SEMANTIC_ALIASES = {
    "ai": "artificial_intelligence",
    "artificial": "artificial_intelligence",
    "intelligence": "artificial_intelligence",
    "machine": "artificial_intelligence",
    "learning": "artificial_intelligence",
    "course": "training",
    "courses": "training",
    "clinic": "training",
    "clinics": "training",
    "training": "training",
    "workshop": "training",
    "workshops": "training",
    "agency": "professional_service",
    "agencies": "professional_service",
    "consultant": "professional_service",
    "consultants": "professional_service",
    "freelance": "professional_service",
    "freelancer": "professional_service",
    "freelancers": "professional_service",
    "hands": "practical",
    "implementation": "practical",
    "practical": "practical",
}
_VECTOR_DIMENSION = 128


def lexical_score(query_text: str, value: str) -> float:
    query = set(tokenize(query_text))
    if not query:
        return 1.0
    values = set(tokenize(value))
    return len(query & values) / len(query)


def semantic_vector(value: str) -> list[float]:
    counts: Counter[int] = Counter()
    for token in tokenize(value):
        canonical = _SEMANTIC_ALIASES.get(token, token)
        digest = hashlib.sha256(canonical.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % _VECTOR_DIMENSION
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        counts[index] += sign
    vector = [float(counts.get(index, 0.0)) for index in range(_VECTOR_DIMENSION)]
    norm = math.sqrt(sum(item * item for item in vector))
    return [item / norm for item in vector] if norm else vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    value = sum(a * b for a, b in zip(left, right, strict=True))
    return max(0.0, min(1.0, value))


def entity_score(query_entities: list[str], record_entities: list[str]) -> float:
    if not query_entities:
        return 0.0
    query = set(query_entities)
    return len(query & set(record_entities)) / len(query)


def provenance_score(record: MemoryRecord) -> float:
    weights = {
        MemoryTrustClass.USER_CONFIRMED: 1.0,
        MemoryTrustClass.EVIDENCE_BOUND: 0.9,
        MemoryTrustClass.VERIFIED_RESULT: 0.85,
        MemoryTrustClass.RECEIPT_BOUND: 0.7,
        MemoryTrustClass.INFERRED: 0.35,
        MemoryTrustClass.UNTRUSTED: 0.1,
    }
    return weights[record.provenance.trust_class]


def tokenize(value: str) -> list[str]:
    return _TOKEN_PATTERN.findall(value.lower())
