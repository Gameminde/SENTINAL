from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import utc_now
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.store import MissionRunStore, _path_exists, _read_text_file
from sentinel.operator.unified_execution_dispatcher import UnifiedDispatchResult
from sentinel.shared.safety_scanner import SHARED_SECRET_LIKE_PATTERN


_SCHEMA_VERSION = "browser_proof_index_v1"
_MAX_EXCERPT_CHARS = 700
_MAX_CLAIM_TEXT_CHARS = 700
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "auth",
    "authorization",
    "bearer",
    "code",
    "cookie",
    "credential",
    "key",
    "password",
    "refresh_token",
    "secret",
    "session",
    "sessionid",
    "sid",
    "token",
}
_FACTUAL_CLAIM_TYPES = {"sourced_factual_claim", "factual_claim"}
_INFERENCE_TYPES = {"model_inference", "recommendation"}
_UNCERTAINTY_TYPES = {"uncertainty", "declared_unknown"}
_CONTRADICTION_TYPES = {"contradiction"}


class BrowserProofIndexBuilder:
    """Builds a safe cross-reference index for existing browser proof artifacts.

    This is deliberately not a new receipt owner. The source of truth remains
    the ProductActionKernel receipt and the browser/session receipts. The index
    only makes those owners inspectable from the root mission/export bundle.
    """

    def __init__(
        self,
        *,
        store: MissionRunStore,
        loop_id: str,
        dispatch_results: tuple[UnifiedDispatchResult, ...] | list[UnifiedDispatchResult],
        final_answer_payload: dict[str, Any] | None = None,
    ) -> None:
        self.store = store
        self.loop_id = loop_id
        self.dispatch_results = tuple(dispatch_results)
        self.final_answer_payload = dict(final_answer_payload or {})

    def build(self, *, status: str = "in_progress", final_reason: str = "") -> dict[str, Any]:
        material_entries: list[dict[str, Any]] = []
        product_receipt_entries: list[dict[str, Any]] = []
        public_evidence: list[dict[str, Any]] = []
        missing_count = 0

        for dispatch in self.dispatch_results:
            product_receipts = self._load_product_receipts(dispatch)
            product_receipt_entries.extend(product_receipts)
            if dispatch.capability_id != "real_browser_control":
                continue
            browser_receipts = self._load_browser_receipts(dispatch)
            if not browser_receipts:
                missing_count += 1
                material_entries.append(self._missing_browser_entry(dispatch, product_receipts))
                continue
            for browser_receipt in browser_receipts:
                material_entries.append(self._browser_entry(dispatch, product_receipts, browser_receipt))
                public_evidence.extend(_evidence_from_browser_receipt(browser_receipt))

        public_evidence.extend(
            sanitize_public_evidence(item)
            for item in _list_payload(self.final_answer_payload.get("public_evidence"))
        )
        public_evidence = _dedupe_by_id(public_evidence)
        evidence_ids = {str(item.get("evidence_id") or "") for item in public_evidence if str(item.get("evidence_id") or "")}
        answer_claims = normalize_answer_claims(
            self.final_answer_payload.get("answer_claims"),
            evidence_ids=evidence_ids,
            fallback_summary=str(self.final_answer_payload.get("safe_summary") or ""),
        )
        readable_count = sum(1 for entry in material_entries if entry.get("browser_receipt_readable") is True)
        index: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "loop_id": self.loop_id,
            "status": redact_operator_text(status),
            "final_reason": redact_operator_text(final_reason),
            "mission_ids": list(dict.fromkeys(result.mission_id for result in self.dispatch_results)),
            "product_receipts": product_receipt_entries,
            "material_browser_receipts": material_entries,
            "material_browser_receipt_count": len(material_entries),
            "browser_receipt_readable_count": readable_count,
            "browser_receipt_missing_count": missing_count,
            "public_evidence": public_evidence,
            "public_evidence_count": len(public_evidence),
            "answer_claims": answer_claims,
            "finalgate_metrics": _finalgate_metrics(
                material_entries=material_entries,
                answer_claims=answer_claims,
                readable_count=readable_count,
                missing_count=missing_count,
            ),
            "replay_behavior": "index_only_no_browser_reopen_research_reextract",
            "created_at": utc_now().isoformat(),
            "data_not_authority": True,
            "authority_effect": "none",
            "can_grant_authority": False,
            "can_execute": False,
        }
        index["proof_index_hash"] = stable_hash({**index, "proof_index_hash": ""})
        return index

    def summary(self) -> dict[str, Any]:
        return summary_from_index(self.build())

    def _load_product_receipts(self, dispatch: UnifiedDispatchResult) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for receipt_ref in dispatch.receipt_refs:
            path = self.store.mission_dir(dispatch.mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
            payload = _load_json_or_none(path)
            receipts.append(
                {
                    "receipt_ref": str(receipt_ref),
                    "mission_id": dispatch.mission_id,
                    "dispatch_id": dispatch.dispatch_id,
                    "operation": dispatch.operation,
                    "readable": payload is not None,
                    "location_ref": _artifact_ref(dispatch.mission_id, "product_action_kernel/receipts", str(receipt_ref)),
                    "receipt_hash": str(payload.get("receipt_hash") or "") if isinstance(payload, dict) else "",
                    "execution_status": str(payload.get("execution_status") or "") if isinstance(payload, dict) else "",
                    "material_action": bool(payload.get("material_action")) if isinstance(payload, dict) else False,
                    "data_not_authority": True,
                    "can_execute": False,
                }
            )
        return receipts

    def _load_browser_receipts(self, dispatch: UnifiedDispatchResult) -> list[dict[str, Any]]:
        directory = self.store.mission_dir(dispatch.mission_id) / "real_browser_control" / "receipts"
        if not _path_exists(directory):
            return []
        receipts: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            payload = _load_json_or_none(path)
            if not isinstance(payload, dict):
                continue
            receipts.append(payload)
        return receipts

    def _missing_browser_entry(
        self,
        dispatch: UnifiedDispatchResult,
        product_receipts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "dispatch_id": dispatch.dispatch_id,
            "mission_id": dispatch.mission_id,
            "capability_id": dispatch.capability_id,
            "operation": dispatch.operation,
            "product_receipt_ref": product_receipts[0]["receipt_ref"] if product_receipts else "",
            "browser_receipt_ref": "",
            "browser_receipt_readable": False,
            "browser_receipt_location_ref": _artifact_ref(dispatch.mission_id, "real_browser_control/receipts", "missing"),
            "missing_reason": "real_browser_control_receipt_not_readable_from_child_mission",
            "data_not_authority": True,
            "can_execute": False,
        }

    def _browser_entry(
        self,
        dispatch: UnifiedDispatchResult,
        product_receipts: list[dict[str, Any]],
        browser_receipt: dict[str, Any],
    ) -> dict[str, Any]:
        receipt_ref = str(browser_receipt.get("receipt_id") or "")
        search_materiality = _bounded_dict(browser_receipt.get("search_materiality"))
        typed_outcome = _bounded_dict(search_materiality.get("typed_search_outcome")) if search_materiality else {}
        return {
            "dispatch_id": dispatch.dispatch_id,
            "mission_id": dispatch.mission_id,
            "capability_id": dispatch.capability_id,
            "operation": dispatch.operation,
            "product_receipt_ref": product_receipts[0]["receipt_ref"] if product_receipts else "",
            "product_receipt_location_ref": product_receipts[0]["location_ref"] if product_receipts else "",
            "browser_receipt_ref": receipt_ref,
            "browser_receipt_location_ref": _artifact_ref(dispatch.mission_id, "real_browser_control/receipts", receipt_ref),
            "browser_receipt_readable": True,
            "action_status": redact_operator_text(str(browser_receipt.get("status") or "")),
            "action_kind": redact_operator_text(str(browser_receipt.get("action_kind") or dispatch.operation)),
            "typed_outcome": typed_outcome,
            "search_materiality": search_materiality,
            "selected_backend_id": redact_operator_text(str(browser_receipt.get("selected_backend_id") or "")),
            "actual_backend_id": redact_operator_text(str(browser_receipt.get("actual_backend_id") or "")),
            "session_backend_kind": redact_operator_text(str(browser_receipt.get("session_backend_kind") or "")),
            "backend_mismatch": bool(browser_receipt.get("backend_mismatch")),
            "root_browser_lease_id_hash": str(browser_receipt.get("root_browser_lease_id_hash") or ""),
            "browser_engine_identity_hash": str(browser_receipt.get("browser_engine_identity_hash") or ""),
            "backend_context_identity_hash": str(browser_receipt.get("backend_context_identity_hash") or ""),
            "page_identity_hash": str(browser_receipt.get("page_identity_hash") or ""),
            "before_state_hash": str(browser_receipt.get("before_state_hash") or ""),
            "after_state_hash": str(browser_receipt.get("after_state_hash") or ""),
            "browser_environment_state_hash": str(browser_receipt.get("browser_environment_state_hash") or ""),
            "evidence_refs": sanitize_operator_refs(_receipt_evidence_refs(browser_receipt)),
            "receipt_payload": _safe_receipt_payload(browser_receipt),
            "receipt_hash": str(browser_receipt.get("receipt_hash") or ""),
            "freshness": str(browser_receipt.get("created_at") or ""),
            "replay_status": redact_operator_text(str(browser_receipt.get("replay_behavior") or "")),
            "cleanup_status": "checked_by_root_task_loop_cleanup",
            "contradictions": [],
            "unknowns": _receipt_unknowns(browser_receipt),
            "data_not_authority": True,
            "can_execute": False,
        }


def write_browser_proof_index(
    *,
    store: MissionRunStore,
    loop_id: str,
    dispatch_results: tuple[UnifiedDispatchResult, ...] | list[UnifiedDispatchResult],
    final_answer_payload: dict[str, Any] | None = None,
    evidence_sink: object | None = None,
    status: str = "in_progress",
    final_reason: str = "",
) -> dict[str, Any]:
    index = BrowserProofIndexBuilder(
        store=store,
        loop_id=loop_id,
        dispatch_results=dispatch_results,
        final_answer_payload=final_answer_payload,
    ).build(status=status, final_reason=final_reason)
    path = store.run_root / "_browser_proof_index" / f"{loop_id}.json"
    store.atomic_write_json(path, index)
    run_dir = getattr(evidence_sink, "run_dir", None)
    if run_dir is not None:
        _atomic_write_json(Path(run_dir) / "browser_proof_index.json", index)
    record = getattr(evidence_sink, "record_transition", None)
    if callable(record):
        record("browser_proof_index_created", summary_from_index(index))
    return index


def summary_from_index(index: dict[str, Any]) -> dict[str, Any]:
    claims = index.get("answer_claims") if isinstance(index.get("answer_claims"), dict) else {}
    return {
        "schema_version": "browser_proof_index_summary_v1",
        "proof_index_hash": str(index.get("proof_index_hash") or ""),
        "material_browser_receipt_count": int(index.get("material_browser_receipt_count") or 0),
        "browser_receipt_readable_count": int(index.get("browser_receipt_readable_count") or 0),
        "browser_receipt_missing_count": int(index.get("browser_receipt_missing_count") or 0),
        "public_evidence_count": int(index.get("public_evidence_count") or 0),
        "public_evidence_ids": [
            str(item.get("evidence_id") or "")
            for item in _list_payload(index.get("public_evidence"))[:12]
            if str(item.get("evidence_id") or "")
        ],
        "answer_claim_counts": {
            "factual_supported": int(claims.get("factual_supported_count") or 0),
            "factual_unsupported": int(claims.get("factual_unsupported_count") or 0),
            "inference": int(claims.get("inference_count") or 0),
            "uncertainty": int(claims.get("uncertainty_count") or 0),
            "declared_unknown": int(claims.get("declared_unknown_count") or 0),
            "contradiction": int(claims.get("contradiction_count") or 0),
            "open_world": int(claims.get("open_world_claim_type_count") or 0),
        },
        "data_not_authority": True,
        "can_execute": False,
    }


def sanitize_public_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    evidence_id = str(payload.get("evidence_id") or f"evidence:{stable_hash(payload)}")
    source_url = str(payload.get("source_url") or payload.get("url") or "")
    normalized_url, origin = _normalize_public_url(source_url)
    source_title = _safe_text(str(payload.get("source_title") or payload.get("title") or ""), limit=220)
    source_origin = _safe_origin(str(payload.get("source_origin") or origin or ""))
    excerpt = _safe_text(str(payload.get("excerpt") or payload.get("bounded_excerpt") or ""), limit=_MAX_EXCERPT_CHARS)
    evidence = {
        "evidence_id": _safe_ref(evidence_id, prefix="evidence"),
        "normalized_public_url": normalized_url,
        "source_title": source_title or "unknown",
        "source_origin": source_origin or "unknown",
        "bounded_excerpt": excerpt,
        "timestamp": str(payload.get("timestamp") or utc_now().isoformat()),
        "digest": stable_hash(
            {
                "url": normalized_url,
                "title": source_title,
                "origin": source_origin,
                "excerpt": excerpt,
            }
        ),
        "receipt_ref": _safe_optional_ref(str(payload.get("receipt_ref") or "")),
        "data_not_authority": True,
        "can_execute": False,
    }
    return evidence


def normalize_answer_claims(
    claims: Any,
    *,
    evidence_ids: set[str],
    fallback_summary: str = "",
) -> dict[str, Any]:
    normalized_claims: list[dict[str, Any]] = []
    if not isinstance(claims, list):
        claims = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        normalized_claims.append(_normalize_claim(claim, index=index, evidence_ids=evidence_ids))
    if not normalized_claims and fallback_summary.strip():
        normalized_claims.append(
            _normalize_claim(
                {
                    "claim_type": "model_inference",
                    "text": fallback_summary,
                    "evidence_refs": [],
                    "confidence": 0.0,
                },
                index=0,
                evidence_ids=evidence_ids,
            )
        )
    counts = _claim_counts(normalized_claims)
    return {
        "schema_version": "browser_answer_claim_candidates_v1",
        "claims": normalized_claims,
        **counts,
        "unsupported_claim_count": counts["factual_unsupported_count"],
        "data_not_authority": True,
        "can_execute": False,
    }


def _normalize_claim(claim: dict[str, Any], *, index: int, evidence_ids: set[str]) -> dict[str, Any]:
    claim_type = str(claim.get("claim_type") or claim.get("type") or "model_inference").strip() or "model_inference"
    text = _safe_text(str(claim.get("text") or claim.get("claim") or ""), limit=_MAX_CLAIM_TEXT_CHARS)
    evidence_refs = sanitize_operator_refs(_list_of_strings(claim.get("evidence_refs")))
    missing_refs = [ref for ref in evidence_refs if ref not in evidence_ids]
    if claim_type in _FACTUAL_CLAIM_TYPES:
        support_status = "supported" if evidence_refs and not missing_refs else "unsupported"
    elif claim_type in _INFERENCE_TYPES:
        support_status = "inference_not_factual_claim"
    elif claim_type in _UNCERTAINTY_TYPES:
        support_status = "uncertainty_or_unknown_not_factual_claim"
    elif claim_type in _CONTRADICTION_TYPES:
        support_status = "contradiction_declared"
    else:
        support_status = "open_world_claim_type_preserved"
    return {
        "claim_id": _safe_ref(str(claim.get("claim_id") or f"claim:{index}"), prefix="claim"),
        "claim_type": redact_operator_text(claim_type)[:120],
        "text": text,
        "evidence_refs": evidence_refs,
        "missing_evidence_refs": missing_refs,
        "support_status": support_status,
        "confidence": _safe_float(claim.get("confidence")),
        "data_not_authority": True,
        "can_execute": False,
    }


def _claim_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    factual_supported = 0
    factual_unsupported = 0
    inference = 0
    uncertainty = 0
    declared_unknown = 0
    contradiction = 0
    open_world = 0
    for claim in claims:
        claim_type = str(claim.get("claim_type") or "")
        support_status = str(claim.get("support_status") or "")
        if claim_type in _FACTUAL_CLAIM_TYPES:
            if support_status == "supported":
                factual_supported += 1
            else:
                factual_unsupported += 1
        elif claim_type in _INFERENCE_TYPES:
            inference += 1
        elif claim_type == "uncertainty":
            uncertainty += 1
        elif claim_type == "declared_unknown":
            declared_unknown += 1
        elif claim_type in _CONTRADICTION_TYPES:
            contradiction += 1
        else:
            open_world += 1
    return {
        "factual_supported_count": factual_supported,
        "factual_unsupported_count": factual_unsupported,
        "inference_count": inference,
        "uncertainty_count": uncertainty,
        "declared_unknown_count": declared_unknown,
        "contradiction_count": contradiction,
        "open_world_claim_type_count": open_world,
    }


def _finalgate_metrics(
    *,
    material_entries: list[dict[str, Any]],
    answer_claims: dict[str, Any],
    readable_count: int,
    missing_count: int,
) -> dict[str, Any]:
    return {
        "material_browser_receipt_count": len(material_entries),
        "readable_material_browser_receipt_count": readable_count,
        "missing_material_browser_receipt_count": missing_count,
        "factual_supported_count": int(answer_claims.get("factual_supported_count") or 0),
        "factual_unsupported_count": int(answer_claims.get("factual_unsupported_count") or 0),
        "inference_count": int(answer_claims.get("inference_count") or 0),
        "uncertainty_count": int(answer_claims.get("uncertainty_count") or 0),
        "declared_unknown_count": int(answer_claims.get("declared_unknown_count") or 0),
        "contradiction_count": int(answer_claims.get("contradiction_count") or 0),
        "open_world_claim_type_count": int(answer_claims.get("open_world_claim_type_count") or 0),
        "data_not_authority": True,
        "can_execute": False,
    }


def _evidence_from_browser_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_refs = _receipt_evidence_refs(receipt)
    if not evidence_refs:
        evidence_refs = [f"evidence:{stable_hash(receipt)}"]
    title = str(receipt.get("page_title") or receipt.get("action_kind") or "browser evidence")
    return [
        sanitize_public_evidence(
            {
                "evidence_id": evidence_refs[0],
                "source_title": title,
                "source_origin": f"origin-hash:{str(receipt.get('safe_url_origin_hash') or '')[:24]}",
                "excerpt": _receipt_excerpt(receipt),
                "receipt_ref": str(receipt.get("receipt_id") or ""),
                "timestamp": str(receipt.get("created_at") or ""),
            }
        )
    ]


def _receipt_evidence_refs(receipt: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    search_materiality = receipt.get("search_materiality")
    if isinstance(search_materiality, dict):
        outcome = search_materiality.get("typed_search_outcome")
        if isinstance(outcome, dict):
            refs.extend(_list_of_strings(outcome.get("evidence_refs")))
    if receipt.get("browser_environment_state_hash"):
        refs.append(f"browser_env_state:{receipt['browser_environment_state_hash']}")
    if receipt.get("receipt_id"):
        refs.append(f"browser_receipt:{receipt['receipt_id']}")
    return list(dict.fromkeys(refs))


def _receipt_excerpt(receipt: dict[str, Any]) -> str:
    action = str(receipt.get("action_kind") or "browser action")
    status = str(receipt.get("status") or "unknown")
    typed_outcome = ""
    search_materiality = receipt.get("search_materiality")
    if isinstance(search_materiality, dict):
        outcome = search_materiality.get("typed_search_outcome")
        if isinstance(outcome, dict):
            typed_outcome = str(outcome.get("outcome_kind") or "")
    suffix = f" typed_outcome={typed_outcome}" if typed_outcome else ""
    return f"{action} status={status}{suffix}"


def _receipt_unknowns(receipt: dict[str, Any]) -> list[str]:
    unknowns: list[str] = []
    if not receipt.get("browser_environment_state_hash"):
        unknowns.append("browser_environment_state_hash_missing")
    if not receipt.get("root_browser_lease_id_hash"):
        unknowns.append("root_browser_lease_id_hash_missing")
    return unknowns


def _safe_receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "receipt_id",
        "mission_id",
        "browser_session_ref",
        "browser_session_handle_ref",
        "browser_session_handle_hash",
        "child_workspace_handle_hash",
        "mission_workspace_ref",
        "mission_workspace_hash",
        "root_browser_lease_id_hash",
        "browser_engine_identity_hash",
        "backend_context_identity_hash",
        "page_identity_hash",
        "bounded_url_ref",
        "safe_url_origin_hash",
        "selected_backend_id",
        "actual_backend_id",
        "session_backend_kind",
        "backend_mismatch",
        "simple_skill",
        "internal_action_id",
        "product_dispatch_owner",
        "stable_element_ref",
        "action_kind",
        "status",
        "recovery_classification",
        "replay_behavior",
        "before_state_hash",
        "after_state_hash",
        "browser_environment_state_hash",
        "search_materiality",
        "bounded_observation_summary_hash",
        "created_at",
        "result_hash",
        "receipt_hash",
        "data_not_authority",
        "authority_effect",
        "can_grant_authority",
        "can_execute",
    }
    payload = {key: _sanitize_value(key, value) for key, value in receipt.items() if key in allowed}
    return payload


def _sanitize_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if "path" in lowered or "selector" in lowered or "raw" in lowered:
        return {"redacted": lowered, "hash": stable_hash(value)}
    if isinstance(value, str):
        return _safe_text(value, limit=1200)
    if isinstance(value, dict):
        return {str(k): _sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value[:30]]
    return value


def _normalize_public_url(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "", ""
    safe_query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.strip().lower() not in _SENSITIVE_QUERY_KEYS and not _looks_secret(item)
    ]
    query = urlencode(safe_query, doseq=True)
    normalized = urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", query, ""))
    return normalized[:700], f"{parsed.scheme}://{parsed.netloc.lower()}"


def _safe_origin(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc.lower()}"[:240]
    if value.startswith("origin-hash:"):
        return redact_operator_text(value[:80])
    return redact_operator_text(value[:240])


def _safe_text(value: str, *, limit: int) -> str:
    rendered = " ".join(str(value or "").split())[:limit]
    if _looks_secret(rendered):
        return "[redacted-secret-like-value]"
    return redact_operator_text(rendered)


def _safe_ref(value: str, *, prefix: str) -> str:
    rendered = str(value or "").strip()
    if not rendered:
        return f"{prefix}:{stable_hash(value)[:24]}"
    if "\\" in rendered or "/" in rendered or ".." in rendered or _looks_secret(rendered):
        return f"{prefix}:{stable_hash(rendered)[:24]}"
    return rendered[:160]


def _safe_optional_ref(value: str) -> str:
    if not value:
        return ""
    return _safe_ref(value, prefix="ref")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _looks_secret(value: str) -> bool:
    if not value:
        return False
    return bool(SHARED_SECRET_LIKE_PATTERN.search(value))


def _bounded_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _sanitize_value(str(key), item) for key, item in value.items()}


def _list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list | tuple | set):
        return []
    return [str(item) for item in value if str(item)]


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("evidence_id") or stable_hash(item))
        if item_id in seen:
            continue
        seen.add(item_id)
        deduped.append(item)
    return deduped


def _artifact_ref(mission_id: str, collection: str, ref: str) -> str:
    return f"mission_artifact:{mission_id}:{collection}:{ref}"


def _load_json_or_none(path: Path) -> dict[str, Any] | None:
    try:
        if not _path_exists(path):
            return None
        payload = json.loads(_read_text_file(path))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, sort_keys=True, indent=2, default=str)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".tmp.", suffix=".tmp", delete=False) as handle:
        temp_path = handle.name
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)
