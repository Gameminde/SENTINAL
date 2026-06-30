from __future__ import annotations

import importlib.util
from typing import Iterable

from pydantic import Field, model_validator

from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


CLOAK_BROWSER_MODULE = "sentinel.organs.browser.cloak_backend"
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
    cloak_available = CLOAK_BROWSER_MODULE in available
    playwright_available = PLAYWRIGHT_BROWSER_MODULE in available
    candidates = (
        BrowserBackendCandidate(
            backend_id="cloak_browser",
            display_name="CloakBrowser live browser backend",
            owner_module=CLOAK_BROWSER_MODULE,
            role="preferred_live_browser_backend",
            available=cloak_available,
        ),
        BrowserBackendCandidate(
            backend_id="playwright_real_browser_engine",
            display_name="Playwright compatibility browser backend",
            owner_module=PLAYWRIGHT_BROWSER_MODULE,
            role="explicit_compatibility_or_test_backend",
            available=playwright_available,
            explicit_compatibility_required=True,
        ),
    )
    if cloak_available:
        return BrowserBackendSelection(
            preferred_backend_id="cloak_browser",
            compatibility_backend_id="playwright_real_browser_engine" if playwright_available else None,
            selection_reason="cloak_browser_backend_available",
            candidates=candidates,
        )
    return BrowserBackendSelection(
        preferred_backend_id=None,
        compatibility_backend_id="playwright_real_browser_engine" if playwright_available else None,
        selection_reason="cloak_browser_backend_unavailable" if playwright_available else "no_browser_backend_available",
        candidates=candidates,
    )


def _discover_available_modules() -> set[str]:
    return {
        module_name
        for module_name in (CLOAK_BROWSER_MODULE, PLAYWRIGHT_BROWSER_MODULE)
        if importlib.util.find_spec(module_name) is not None
    }


__all__ = [
    "BrowserBackendCandidate",
    "BrowserBackendSelection",
    "CLOAK_BROWSER_MODULE",
    "PLAYWRIGHT_BROWSER_MODULE",
    "select_browser_backend",
]
