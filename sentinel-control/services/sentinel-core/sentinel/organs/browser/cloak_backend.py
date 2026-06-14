from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse


class BrowserSessionEngineError(RuntimeError):
    """Raised when a browser session backend cannot complete an engine operation."""


@dataclass
class BrowserEngineSession:
    backend_kind: str
    context: Any
    page: Any
    profile_dir: Path
    owner: Any | None = None
    network_events: list[dict[str, Any]] | None = None
    console_messages: list[dict[str, Any]] | None = None

    def close(self) -> None:
        try:
            self.context.close()
        finally:
            owner = self.owner
            if owner is None:
                return
            close = getattr(owner, "close", None)
            if callable(close):
                close()
            stop = getattr(owner, "stop", None)
            if callable(stop):
                stop()


class BrowserSessionBackend(Protocol):
    backend_kind: str

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserEngineSession: ...


class CloakBrowserSessionBackend:
    """Sentinel adapter for CloakBrowser's persistent stealth browser context."""

    backend_kind = "cloakbrowser"

    def __init__(
        self,
        *,
        document_fixtures: dict[str, str] | None = None,
        headless: bool = True,
        humanize: bool = True,
        stealth_args: bool = True,
        page_javascript_enabled: bool = True,
        accept_downloads: bool = False,
    ) -> None:
        self.document_fixtures = document_fixtures or {}
        self.headless = headless
        self.humanize = humanize
        self.stealth_args = stealth_args
        self.page_javascript_enabled = page_javascript_enabled
        self.accept_downloads = accept_downloads

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserEngineSession:
        try:
            import cloakbrowser  # type: ignore[import-not-found]
        except ImportError as exc:
            raise BrowserSessionEngineError(
                "cloakbrowser_not_installed; install sentinel-core[cloak] or choose the playwright compatibility engine"
            ) from exc

        profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            context = cloakbrowser.launch_persistent_context(
                str(profile_dir),
                headless=self.headless,
                stealth_args=self.stealth_args,
                humanize=self.humanize,
                viewport={"width": viewport_width, "height": viewport_height},
                accept_downloads=self.accept_downloads,
                java_script_enabled=self.page_javascript_enabled,
            )
            _install_context_fixture_route(context, self.document_fixtures, url)
            page = context.new_page()
            network_events: list[dict[str, Any]] = []
            console_messages: list[dict[str, Any]] = []
            _install_metadata_listeners(page, network_events, console_messages)
            _install_fixture_route(page, self.document_fixtures, url)
            _goto_document(page, url, timeout_ms)
            return BrowserEngineSession(
                backend_kind=self.backend_kind,
                context=context,
                page=page,
                profile_dir=profile_dir,
                network_events=network_events,
                console_messages=console_messages,
            )
        except BrowserSessionEngineError:
            raise
        except Exception as exc:
            raise BrowserSessionEngineError(f"cloakbrowser_open_failed:{type(exc).__name__}") from exc


class PlaywrightSessionBackend:
    """Compatibility backend for deterministic tests and local development fallback."""

    backend_kind = "playwright_compat"

    def __init__(
        self,
        *,
        document_fixtures: dict[str, str] | None = None,
        headless: bool = True,
        page_javascript_enabled: bool = True,
        accept_downloads: bool = False,
    ) -> None:
        self.document_fixtures = document_fixtures or {}
        self.headless = headless
        self.page_javascript_enabled = page_javascript_enabled
        self.accept_downloads = accept_downloads

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserEngineSession:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserSessionEngineError("playwright_not_installed") from exc

        profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=self.headless)
            context = browser.new_context(
                accept_downloads=self.accept_downloads,
                java_script_enabled=self.page_javascript_enabled,
                storage_state=None,
                viewport={"width": viewport_width, "height": viewport_height},
            )
            _install_context_fixture_route(context, self.document_fixtures, url)
            page = context.new_page()
            network_events: list[dict[str, Any]] = []
            console_messages: list[dict[str, Any]] = []
            _install_metadata_listeners(page, network_events, console_messages)
            _install_fixture_route(page, self.document_fixtures, url)
            _goto_document(page, url, timeout_ms)
            return BrowserEngineSession(
                backend_kind=self.backend_kind,
                context=context,
                page=page,
                profile_dir=profile_dir,
                owner=_PlaywrightOwner(browser=browser, playwright=playwright),
                network_events=network_events,
                console_messages=console_messages,
            )
        except BrowserSessionEngineError:
            raise
        except Exception as exc:
            raise BrowserSessionEngineError(f"playwright_open_failed:{type(exc).__name__}") from exc


@dataclass
class _PlaywrightOwner:
    browser: Any
    playwright: Any

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            self.playwright.stop()


def _install_fixture_route(page: Any, document_fixtures: dict[str, str], initial_url: str) -> None:
    if not document_fixtures:
        return
    page.route("**/*", lambda route, request: _route_request(route, request, initial_url, document_fixtures))


def _install_context_fixture_route(context: Any, document_fixtures: dict[str, str], initial_url: str) -> None:
    if not document_fixtures:
        return
    route = getattr(context, "route", None)
    if callable(route):
        route("**/*", lambda request_route, request: _route_request(request_route, request, initial_url, document_fixtures))


def _install_metadata_listeners(
    page: Any,
    network_events: list[dict[str, Any]],
    console_messages: list[dict[str, Any]],
) -> None:
    on = getattr(page, "on", None)
    if not callable(on):
        return

    def _request_finished(request: Any) -> None:
        try:
            response = request.response()
            network_events.append(
                {
                    "url_host": (urlparse(str(getattr(request, "url", ""))).hostname or "").lower(),
                    "method": str(getattr(request, "method", "GET")).upper(),
                    "resource_type": str(getattr(request, "resource_type", "")),
                    "status": int(getattr(response, "status", 0) or 0) if response is not None else 0,
                }
            )
        except Exception:
            network_events.append({"status": 0, "error": "request_finished_metadata_failed"})

    def _request_failed(request: Any) -> None:
        try:
            network_events.append(
                {
                    "url_host": (urlparse(str(getattr(request, "url", ""))).hostname or "").lower(),
                    "method": str(getattr(request, "method", "GET")).upper(),
                    "resource_type": str(getattr(request, "resource_type", "")),
                    "status": 0,
                    "error": "request_failed",
                }
            )
        except Exception:
            network_events.append({"status": 0, "error": "request_failed_metadata_failed"})

    def _console(message: Any) -> None:
        try:
            console_messages.append(
                {
                    "type": str(getattr(message, "type", "")),
                    "text_hash": _stable_text_hash(str(getattr(message, "text", ""))),
                }
            )
        except Exception:
            console_messages.append({"type": "unknown", "text_hash": _stable_text_hash("console_metadata_failed")})

    on("requestfinished", _request_finished)
    on("requestfailed", _request_failed)
    on("console", _console)


def _route_request(route: Any, route_request: Any, initial_url: str, document_fixtures: dict[str, str]) -> None:
    if getattr(route_request, "resource_type", "") != "document":
        route.abort()
        return
    request_url = str(getattr(route_request, "url", ""))
    if not _same_origin(request_url, initial_url):
        route.abort()
        return
    fixture = document_fixtures.get(request_url)
    if fixture is not None:
        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=fixture)
        return
    route.continue_()


def _goto_document(page: Any, url: str, timeout_ms: int) -> None:
    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    if response is None:
        return
    status = int(getattr(response, "status", 0) or 0)
    if status and not 200 <= status <= 299:
        raise BrowserSessionEngineError(f"browser_session_open_status:{status}")


def _same_origin(left: str, right: str) -> bool:
    left_parsed = urlparse(left)
    right_parsed = urlparse(right)
    return (
        left_parsed.scheme.lower(),
        (left_parsed.hostname or "").lower(),
        left_parsed.port,
    ) == (
        right_parsed.scheme.lower(),
        (right_parsed.hostname or "").lower(),
        right_parsed.port,
    )


def _stable_text_hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
