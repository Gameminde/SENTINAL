from __future__ import annotations

import time
from datetime import UTC, datetime
from html.parser import HTMLParser

from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.models import (
    BrowserConsoleRecord,
    BrowserHealthMetadata,
    BrowserPageErrorRecord,
    BrowserRenderedElementScreenshot,
    BrowserRenderedPage,
    BrowserRenderedSnapshotRequest,
    BrowserRequestFailureRecord,
    BrowserRequestRecord,
    BrowserResponseRecord,
)
from sentinel.organs.browser.observability import build_browser_network_ledger
from sentinel.organs.browser.rendered_snapshot import BrowserRenderError


class PlaywrightReadOnlyRenderer:
    """Rendered read-only browser backend for Browser V1.

    Authority profile:
    - fresh browser context per render;
    - JavaScript disabled;
    - downloads disabled;
    - no storage state provided;
    - only the initial document URL is allowed;
    - redirects and subresources are aborted by route policy;
    - no arbitrary page script evaluation.
    """

    def __init__(
        self,
        *,
        timeout_ms: int = 15_000,
        viewport_width: int = 1280,
        viewport_height: int = 900,
        document_fixtures: dict[str, str] | None = None,
    ) -> None:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive.")
        if viewport_width <= 0 or viewport_height <= 0:
            raise ValueError("viewport dimensions must be positive.")
        self.timeout_ms = timeout_ms
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.document_fixtures = document_fixtures or {}

    def __call__(self, request: BrowserRenderedSnapshotRequest, final_url: str) -> BrowserRenderedPage:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserRenderError("playwright_not_installed") from exc

        request_records: list[BrowserRequestRecord] = []
        response_records: list[BrowserResponseRecord] = []
        failure_records: list[BrowserRequestFailureRecord] = []
        console_records: list[BrowserConsoleRecord] = []
        page_error_records: list[BrowserPageErrorRecord] = []
        request_ids: dict[int, str] = {}
        started = time.perf_counter()

        def timestamp() -> str:
            return datetime.now(UTC).isoformat()

        def request_id_for(playwright_request) -> str:
            key = id(playwright_request)
            existing = request_ids.get(key)
            if existing:
                return existing
            request_id = f"r{len(request_ids) + 1}"
            request_ids[key] = request_id
            return request_id

        def record_request(playwright_request) -> None:
            request_id = request_id_for(playwright_request)
            request_records.append(
                BrowserRequestRecord(
                    id=request_id,
                    method=str(getattr(playwright_request, "method", "GET") or "GET"),
                    url=str(getattr(playwright_request, "url", "")),
                    resource_type=str(getattr(playwright_request, "resource_type", "") or "") or None,
                    timestamp=timestamp(),
                )
            )

        def record_response(playwright_response) -> None:
            playwright_request = getattr(playwright_response, "request", None)
            response_records.append(
                BrowserResponseRecord(
                    request_id=request_id_for(playwright_request) if playwright_request is not None else f"r{len(request_ids) + 1}",
                    url=str(getattr(playwright_response, "url", "")),
                    status=int(getattr(playwright_response, "status", 0) or 0) or None,
                    ok=bool(getattr(playwright_response, "ok", False)),
                    content_type=_response_content_type(playwright_response),
                    timestamp=timestamp(),
                )
            )

        def record_request_failure(playwright_request) -> None:
            failure = getattr(playwright_request, "failure", None)
            failure_payload = failure() if callable(failure) else failure
            error_text = ""
            if isinstance(failure_payload, dict):
                error_text = str(failure_payload.get("errorText") or failure_payload.get("error_text") or "")
            elif failure_payload:
                error_text = str(failure_payload)
            failure_records.append(
                BrowserRequestFailureRecord(
                    request_id=request_id_for(playwright_request),
                    url=str(getattr(playwright_request, "url", "")),
                    error_text=error_text or "request_failed",
                    resource_type=str(getattr(playwright_request, "resource_type", "") or "") or None,
                    timestamp=timestamp(),
                )
            )

        def record_console(message) -> None:
            console_records.append(
                BrowserConsoleRecord(
                    type=str(getattr(message, "type", "") or "log"),
                    text=str(getattr(message, "text", "") or ""),
                    location=_console_location(message),
                    timestamp=timestamp(),
                )
            )

        def record_page_error(error) -> None:
            page_error_records.append(
                BrowserPageErrorRecord(
                    message=str(error),
                    name=type(error).__name__,
                    stack=str(getattr(error, "stack", "") or "") or None,
                    timestamp=timestamp(),
                )
            )

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        accept_downloads=False,
                        java_script_enabled=False,
                        storage_state=None,
                        viewport={"width": self.viewport_width, "height": self.viewport_height},
                    )
                    page = context.new_page()
                    page.on("request", record_request)
                    page.on("response", record_response)
                    page.on("requestfailed", record_request_failure)
                    page.on("console", record_console)
                    page.on("pageerror", record_page_error)
                    page.route("**/*", lambda route, route_request: self._route_request(route, route_request, final_url))
                    response = page.goto(final_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    status_code = response.status if response is not None else 0
                    if page.url != final_url:
                        raise BrowserRenderError(f"rendered_final_url_changed:{page.url}")
                    html = page.content()
                    parsed = _RenderedHtmlParser(final_url)
                    parsed.feed(html)
                    parsed.close()
                    text = page.locator("body").inner_text(timeout=self.timeout_ms)
                    screenshot = page.screenshot(type="png", full_page=True, timeout=self.timeout_ms) if request.capture_screenshot else None
                    accessibility_snapshot = BrowserAccessibilitySnapshotBuilder().build(html=html, text=text)
                    pdf_bytes = page.pdf(print_background=True) if request.capture_pdf else None
                    element_screenshots = self._element_screenshots(page, accessibility_snapshot, request)
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    network_ledger = build_browser_network_ledger(
                        requests=request_records,
                        responses=response_records,
                        failures=failure_records,
                        console=console_records,
                        page_errors=page_error_records,
                        health=BrowserHealthMetadata(
                            renderer="playwright_readonly",
                            status="captured",
                            duration_ms=duration_ms,
                            page_url=page.url,
                        ),
                        max_records=request.max_ledger_records,
                    )
                    return BrowserRenderedPage(
                        final_url=page.url,
                        status_code=status_code,
                        title=page.title(),
                        text=text,
                        links=parsed.links,
                        html=html,
                        screenshot_png=screenshot,
                        pdf_bytes=pdf_bytes,
                        element_screenshots=element_screenshots,
                        accessibility_snapshot=accessibility_snapshot,
                        network_ledger=network_ledger,
                    )
                finally:
                    browser.close()
        except BrowserRenderError:
            raise
        except PlaywrightTimeoutError as exc:
            raise BrowserRenderError("browser_render_timeout") from exc
        except PlaywrightError as exc:
            raise BrowserRenderError(str(exc).splitlines()[0]) from exc

    def _route_request(self, route, route_request, final_url: str) -> None:
        if route_request.url != final_url or route_request.resource_type != "document":
            route.abort()
            return
        fixture = self.document_fixtures.get(final_url)
        if fixture is not None:
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=fixture)
            return
        route.continue_()

    def _element_screenshots(self, page, accessibility_snapshot, request: BrowserRenderedSnapshotRequest) -> list[BrowserRenderedElementScreenshot]:
        if not request.capture_element_screenshots:
            return []
        refs = request.element_screenshot_ref_ids or sorted(accessibility_snapshot.refs)[: request.max_element_screenshots]
        screenshots: list[BrowserRenderedElementScreenshot] = []
        for ref_id in refs[: request.max_element_screenshots]:
            ref = accessibility_snapshot.refs.get(ref_id)
            if ref is None:
                continue
            locator = page.get_by_role(ref.role, name=ref.name, exact=True).nth(ref.nth or 0) if ref.name else page.get_by_role(ref.role).nth(ref.nth or 0)
            bbox = locator.bounding_box(timeout=self.timeout_ms) or {}
            screenshots.append(
                BrowserRenderedElementScreenshot(
                    ref_id=ref_id,
                    role=ref.role,
                    name=ref.name,
                    bbox={key: float(value) for key, value in bbox.items()},
                    png=locator.screenshot(type="png", timeout=self.timeout_ms),
                )
            )
        return screenshots


def _response_content_type(playwright_response) -> str | None:
    headers = getattr(playwright_response, "headers", None)
    header_map = headers() if callable(headers) else headers
    if not isinstance(header_map, dict):
        return None
    for key, value in header_map.items():
        if str(key).lower() == "content-type":
            return str(value)
    return None


def _console_location(message) -> dict:
    location = getattr(message, "location", None)
    value = location() if callable(location) else location
    return value if isinstance(value, dict) else {}


class _RenderedHtmlParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            from urllib.parse import urljoin

            self.links.append(urljoin(self.base_url, href))
