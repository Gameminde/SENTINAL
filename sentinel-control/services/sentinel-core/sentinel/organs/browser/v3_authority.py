from __future__ import annotations

from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import Field

from sentinel.shared.models import SentinelModel, new_id


class BrowserV3AuthorityClass(StrEnum):
    FORM_SUBMIT = "browser_form_submit"
    DOWNLOAD_QUARANTINE = "browser_download_quarantine"
    UPLOAD_AUTHORIZED = "browser_upload_authorized"
    PRIVATE_SESSION = "browser_private_session"
    LOGIN_AUTHORITY = "browser_login_authority"
    COOKIE_STORAGE_CONTRACT = "browser_cookie_storage_contract"
    JS_EVALUATE_SANDBOXED = "browser_js_evaluate_sandboxed"
    HAR_BODY_CAPTURE = "browser_har_body_capture"


class BrowserV3AuthorityGrant(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bv3grant"))
    authority_class: BrowserV3AuthorityClass
    allowed_domains: list[str] = Field(default_factory=list)
    max_uses: int = Field(default=1, ge=1, le=100)
    allow_cross_origin: bool = False
    require_context_pack: bool = True
    require_tool_intent_compilation: bool = True
    require_certified_plan: bool = True
    require_pre_snapshot: bool = True
    require_post_snapshot: bool = True
    allowed_mime_types: list[str] = Field(default_factory=list)
    allowed_artifact_ids: list[str] = Field(default_factory=list)
    allowed_accounts: list[str] = Field(default_factory=list)
    allowed_script_hashes: list[str] = Field(default_factory=list)
    max_bytes: int | None = Field(default=None, ge=1, le=500_000_000)
    max_records: int | None = Field(default=None, ge=1, le=100_000)
    max_result_bytes: int | None = Field(default=None, ge=1, le=100_000_000)
    quarantine_path: str = "browser/download_quarantine"
    session_scope: str = "per_mission"
    storage_allowed: bool = False
    redaction_required: bool = True
    credential_source: str = "sentinel_vault"
    blocked_flow_types: list[str] = Field(
        default_factory=lambda: ["payment", "credential", "login", "upload", "download"]
    )
    notes: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserV3RequestModel(SentinelModel):
    mission_id: str
    authority_class: BrowserV3AuthorityClass
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    trace_refs: list[str] = Field(default_factory=list)


class BrowserV3Receipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bv3rec"))
    mission_id: str
    authority_class: BrowserV3AuthorityClass
    authority_grant_id: str
    request_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    trace_refs: list[str] = Field(default_factory=list)


def parse_browser_v3_authority_grants(raw_grants: list[dict[str, Any]]) -> list[BrowserV3AuthorityGrant]:
    grants: list[BrowserV3AuthorityGrant] = []
    for raw in raw_grants:
        if isinstance(raw, dict):
            grants.append(BrowserV3AuthorityGrant(**raw))
    return grants


def find_browser_v3_authority_grant(
    raw_grants: list[dict[str, Any]],
    authority_class: BrowserV3AuthorityClass | str,
    *,
    grant_id: str | None = None,
) -> BrowserV3AuthorityGrant | None:
    target = str(authority_class.value if hasattr(authority_class, "value") else authority_class)
    for grant in parse_browser_v3_authority_grants(raw_grants):
        if grant.authority_class.value != target:
            continue
        if grant_id and grant.id != grant_id:
            continue
        return grant
    return None


def browser_v3_grant_allows_url(grant: BrowserV3AuthorityGrant, url: str) -> bool:
    if not grant.allowed_domains:
        return True
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in grant.allowed_domains)
