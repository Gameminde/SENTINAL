from __future__ import annotations

import importlib.util
from typing import Iterable

from pydantic import Field, model_validator

from sentinel.operator.browser_backend_contract import (
    CLOAK_BROWSER_BACKEND_ID,
    PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
    SENTINEL_CHROMIUM_BACKEND_ID,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


CLOAK_BROWSER_MODULE = "sentinel.organs.browser.cloak_backend"
SENTINEL_CHROMIUM_BROWSER_MODULE = "sentinel.organs.browser.sentinel_chromium_backend"
PLAYWRIGHT_BROWSER_MODULE = "sentinel.operator.real_browser_control_runtime"


class BrowserBackendCandidate(SentinelModel):
    backend_id: str
    display_name: str
    owner_module: str
    role: str
    available: bool
    explicit_compatibility_required: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _candidate_is_data_only(self) -> "BrowserBackendCandidate":
        assert_data_not_authority(
            context="browser_backend_candidate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class BrowserBackendSelection(SentinelModel):
    model_visible_backend_id: str = "browser_skill"
    preferred_backend_id: str | None = None
    compatibility_backend_id: str | None = None
    playwright_requires_explicit_compatibility: bool = True
    selection_reason: str
    candidates: tuple[BrowserBackendCandidate, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _selection_is_data_only(self) -> "BrowserBackendSelection":
        assert_data_not_authority(
            context="browser_backend_selection",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def select_browser_backend(
    *,
    available_backend_modules: Iterable[str] | None = None,
) -> BrowserBackendSelection:
    available = set(available_backend_modules) if available_backend_modules is not None else _discover_available_modules()
    sentinel_chromium_available = SENTINEL_CHROMIUM_BROWSER_MODULE in available
    cloak_available = CLOAK_BROWSER_MODULE in available
    playwright_available = PLAYWRIGHT_BROWSER_MODULE in available
    candidates = (
        BrowserBackendCandidate(
            backend_id=SENTINEL_CHROMIUM_BACKEND_ID,
            display_name="Sentinel Chromium sovereign browser backend",
            owner_module=SENTINEL_CHROMIUM_BROWSER_MODULE,
            role="canonical_browser_backend",
            available=sentinel_chromium_available,
        ),
        BrowserBackendCandidate(
            backend_id=CLOAK_BROWSER_BACKEND_ID,
            display_name="CloakBrowser optional external browser backend",
            owner_module=CLOAK_BROWSER_MODULE,
            role="optional_external_backend",
            available=cloak_available,
            explicit_compatibility_required=True,
        ),
        BrowserBackendCandidate(
            backend_id=PLAYWRIGHT_REAL_BROWSER_BACKEND_ID,
            display_name="Playwright internal Chromium control mechanism",
            owner_module=PLAYWRIGHT_BROWSER_MODULE,
            role="internal_open_source_mechanism_or_explicit_test_backend",
            available=playwright_available,
            explicit_compatibility_required=True,
        ),
    )
    if sentinel_chromium_available:
        return BrowserBackendSelection(
            preferred_backend_id=SENTINEL_CHROMIUM_BACKEND_ID,
            compatibility_backend_id=PLAYWRIGHT_REAL_BROWSER_BACKEND_ID if playwright_available else None,
            selection_reason="sentinel_chromium_backend_available",
            candidates=candidates,
        )
    return BrowserBackendSelection(
        preferred_backend_id=None,
        compatibility_backend_id=PLAYWRIGHT_REAL_BROWSER_BACKEND_ID if playwright_available else None,
        selection_reason="sentinel_chromium_backend_unavailable" if playwright_available or cloak_available else "no_browser_backend_available",
        candidates=candidates,
    )


def _discover_available_modules() -> set[str]:
    return {
        module_name
        for module_name in (SENTINEL_CHROMIUM_BROWSER_MODULE, CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)
        if importlib.util.find_spec(module_name) is not None
    }


__all__ = [
    "BrowserBackendCandidate",
    "BrowserBackendSelection",
    "CLOAK_BROWSER_MODULE",
    "PLAYWRIGHT_BROWSER_MODULE",
    "SENTINEL_CHROMIUM_BROWSER_MODULE",
    "select_browser_backend",
]
