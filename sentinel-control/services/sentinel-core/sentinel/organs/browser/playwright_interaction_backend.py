from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.interaction_execution import P3H_ALLOWED_EXECUTION_INTENTS
from sentinel.organs.browser.models import (
    BrowserAccessibilitySnapshot,
    BrowserInteractionBackendResult,
    BrowserInteractionExecutionRequest,
    BrowserInteractionIntent,
    BrowserInteractionStep,
    BrowserRenderedPage,
)
from sentinel.organs.browser.rendered_snapshot import BrowserRenderError


class PlaywrightLimitedInteractionBackend:
    """Fresh-context Playwright backend for P3H limited browser interactions."""

    def __init__(
        self,
        *,
        viewport_width: int = 1280,
        viewport_height: int = 900,
        document_fixtures: dict[str, str] | None = None,
    ) -> None:
        if viewport_width <= 0 or viewport_height <= 0:
            raise ValueError("viewport dimensions must be positive.")
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.document_fixtures = document_fixtures or {}

    def __call__(self, request: BrowserInteractionExecutionRequest) -> BrowserInteractionBackendResult:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserRenderError("playwright_not_installed") from exc

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
                    page.route("**/*", lambda route, route_request: self._route_request(route, route_request, request.final_url))
                    response = page.goto(request.final_url, wait_until="domcontentloaded", timeout=request.timeout_ms)
                    if response is None or not 200 <= int(response.status) <= 299:
                        raise BrowserRenderError(f"browser_interaction_initial_status:{getattr(response, 'status', 0)}")
                    before_snapshot = self._snapshot(page, request.timeout_ms)
                    if before_snapshot.snapshot_sha256 != request.plan.snapshot_sha256:
                        raise BrowserRenderError("browser_interaction_before_snapshot_mismatch")
                    if before_snapshot.page_sha256 != request.plan.page_sha256:
                        raise BrowserRenderError("browser_interaction_before_page_mismatch")

                    executed_step_ids: list[str] = []
                    for step in request.plan.steps:
                        self._execute_step(page, step, request.timeout_ms)
                        executed_step_ids.append(step.id)
                    page.wait_for_load_state("domcontentloaded", timeout=request.timeout_ms)
                    after_page = self._page_payload(page, request)
                    return BrowserInteractionBackendResult(
                        before_snapshot=before_snapshot,
                        after_page=after_page,
                        final_url_before=request.final_url,
                        final_url_after=page.url,
                        executed_step_ids=executed_step_ids,
                    )
                finally:
                    browser.close()
        except BrowserRenderError:
            raise
        except PlaywrightTimeoutError as exc:
            raise BrowserRenderError("browser_interaction_timeout") from exc
        except PlaywrightError as exc:
            raise BrowserRenderError(str(exc).splitlines()[0]) from exc

    def _execute_step(self, page, step: BrowserInteractionStep, timeout_ms: int) -> None:
        if step.intent not in P3H_ALLOWED_EXECUTION_INTENTS:
            raise BrowserRenderError(f"browser_interaction_intent_not_delegated:{step.intent.value}")
        timeout = step.timeout_ms or timeout_ms
        if step.intent == BrowserInteractionIntent.WAIT_FOR_TEXT_PLAN:
            page.get_by_text(step.text or "").first.wait_for(state="visible", timeout=timeout)
            return
        if step.intent == BrowserInteractionIntent.WAIT_FOR_SELECTOR_PLAN:
            page.locator(step.target.selector or "").first.wait_for(state="visible", timeout=timeout)
            return
        if step.intent == BrowserInteractionIntent.WAIT_FOR_URL_PLAN:
            page.wait_for_url(step.target.url or "", timeout=timeout)
            return

        locator = self._locator_for_ref(page, step)
        if step.intent == BrowserInteractionIntent.CLICK_PLAN:
            locator.click(timeout=timeout)
            return
        if step.intent in {BrowserInteractionIntent.TYPE_PLAN, BrowserInteractionIntent.FILL_PLAN}:
            locator.fill(step.text or "", timeout=timeout)
            return
        if step.intent == BrowserInteractionIntent.SELECT_PLAN:
            locator.select_option(step.values, timeout=timeout)
            return
        if step.intent == BrowserInteractionIntent.HOVER_PLAN:
            locator.hover(timeout=timeout)
            return
        raise BrowserRenderError(f"browser_interaction_intent_not_implemented:{step.intent.value}")

    @staticmethod
    def _locator_for_ref(page, step: BrowserInteractionStep):
        role = step.target.role
        if not role:
            raise BrowserRenderError(f"browser_interaction_ref_role_missing:{step.target.ref}")
        nth = step.target.nth or 0
        if step.target.name:
            return page.get_by_role(role, name=step.target.name, exact=True).nth(nth)
        return page.get_by_role(role).nth(nth)

    def _page_payload(self, page, request: BrowserInteractionExecutionRequest) -> BrowserRenderedPage:
        html = page.content()
        parsed = _RenderedHtmlParser(page.url)
        parsed.feed(html)
        parsed.close()
        text = page.locator("body").inner_text(timeout=request.timeout_ms)
        screenshot = page.screenshot(type="png", full_page=True, timeout=request.timeout_ms) if request.capture_screenshot else None
        return BrowserRenderedPage(
            final_url=page.url,
            status_code=200,
            title=page.title(),
            text=text,
            links=parsed.links,
            html=html,
            screenshot_png=screenshot,
            accessibility_snapshot=BrowserAccessibilitySnapshotBuilder().build(html=html, text=text),
        )

    @staticmethod
    def _snapshot(page, timeout_ms: int) -> BrowserAccessibilitySnapshot:
        html = page.content()
        text = page.locator("body").inner_text(timeout=timeout_ms)
        return BrowserAccessibilitySnapshotBuilder().build(html=html, text=text)

    def _route_request(self, route, route_request, initial_url: str) -> None:
        if route_request.resource_type != "document":
            route.abort()
            return
        if not _same_origin(route_request.url, initial_url):
            route.abort()
            return
        fixture = self.document_fixtures.get(route_request.url)
        if fixture is not None:
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=fixture)
            return
        route.continue_()


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
            self.links.append(urljoin(self.base_url, href))
