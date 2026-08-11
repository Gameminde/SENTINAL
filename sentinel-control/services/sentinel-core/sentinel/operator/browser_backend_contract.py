from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sentinel.mission.models import MissionAuthorityEnvelope


SENTINEL_CHROMIUM_BACKEND_ID = "sentinel_chromium"
SENTINEL_CHROMIUM_SESSION_KIND = "sentinel_chromium"
CLOAK_BROWSER_BACKEND_ID = "cloak_browser"
CLOAK_BROWSER_SESSION_KIND = "cloakbrowser"
PLAYWRIGHT_REAL_BROWSER_BACKEND_ID = "playwright_real_browser_engine"
PLAYWRIGHT_COMPAT_SESSION_KIND = "playwright_compat"


@runtime_checkable
class BrowserBackend(Protocol):
    """Minimal Sentinel-owned browser engine surface consumed by product code."""

    browser_backend_id: str

    @property
    def safe_url_origin_hash(self) -> str: ...

    @property
    def session_manager_backend_kind(self) -> str: ...

    def bind_authority(self, authority: MissionAuthorityEnvelope) -> None: ...

    def bind_root_session_id(self, root_session_id: str) -> None: ...

    def open(self) -> Any: ...

    def observe(self) -> Any: ...

    def close(self) -> None: ...


__all__ = [
    "BrowserBackend",
    "CLOAK_BROWSER_BACKEND_ID",
    "CLOAK_BROWSER_SESSION_KIND",
    "PLAYWRIGHT_COMPAT_SESSION_KIND",
    "PLAYWRIGHT_REAL_BROWSER_BACKEND_ID",
    "SENTINEL_CHROMIUM_BACKEND_ID",
    "SENTINEL_CHROMIUM_SESSION_KIND",
]
