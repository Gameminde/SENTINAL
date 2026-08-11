from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sentinel.operator.browser_backend_contract import SENTINEL_CHROMIUM_SESSION_KIND
from sentinel.organs.browser.cloak_backend import (
    BrowserEngineSession,
    BrowserSessionEngineError,
    PlaywrightSessionBackend,
)


class SentinelChromiumSessionBackend:
    """Canonical sovereign Chromium backend.

    Playwright is used only as an internal open-source control mechanism here.
    Product code receives Sentinel session models and never receives Playwright
    objects or selectors as authority-bearing capabilities.
    """

    backend_kind = SENTINEL_CHROMIUM_SESSION_KIND

    def __init__(
        self,
        *,
        document_fixtures: dict[str, str] | None = None,
        headless: bool = True,
        page_javascript_enabled: bool = True,
        accept_downloads: bool = False,
        lifecycle_event_sink: Callable[..., None] | None = None,
    ) -> None:
        self._lifecycle_event_sink = lifecycle_event_sink
        self._backend = PlaywrightSessionBackend(
            document_fixtures=document_fixtures,
            headless=headless,
            page_javascript_enabled=page_javascript_enabled,
            accept_downloads=accept_downloads,
        )

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserEngineSession:
        self._emit_lifecycle_event("sentinel_chromium_open_context", "stage_started")
        try:
            session = self._backend.open_context(
                profile_dir=profile_dir,
                url=url,
                timeout_ms=timeout_ms,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
            )
        except BrowserSessionEngineError as exc:
            self._emit_lifecycle_event("sentinel_chromium_open_context", "stage_failed", exception=exc)
            raise
        except Exception as exc:
            self._emit_lifecycle_event("sentinel_chromium_open_context", "stage_failed", exception=exc)
            raise BrowserSessionEngineError(f"sentinel_chromium_open_failed:{type(exc).__name__}") from exc
        session.backend_kind = self.backend_kind
        self._emit_lifecycle_event("sentinel_chromium_open_context", "stage_returned")
        return session

    def _emit_lifecycle_event(
        self,
        stage: str,
        event: str,
        *,
        details: dict[str, Any] | None = None,
        exception: BaseException | None = None,
        failure_code: str | None = None,
    ) -> None:
        sink = self._lifecycle_event_sink
        if sink is None:
            return
        try:
            sink(stage, event, details=details, exception=exception, failure_code=failure_code)
        except Exception:
            return


__all__ = ["SentinelChromiumSessionBackend"]
