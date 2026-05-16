from __future__ import annotations

from pydantic import Field

from sentinel.organs.browser.models import BrowserPublicTab
from sentinel.organs.browser.public_lifecycle import BrowserPublicLifecycleController
from sentinel.organs.browser.url_guard import DnsResolver
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserPublicTabPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("btabplan"))
    url: str
    purpose: str
    tab_id: str | None = None


class BrowserMultitabStrategyResult(SentinelModel):
    accepted: bool
    reason: str
    mission_id: str
    session_id: str | None = None
    tabs: list[BrowserPublicTab] = Field(default_factory=list)
    strategy_sha256: str | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserPublicMultitabOperator:
    """Executes public/stateless multi-tab lifecycle strategy through the existing lifecycle controller."""

    def __init__(self, *, lifecycle: BrowserPublicLifecycleController | None = None) -> None:
        self.lifecycle = lifecycle or BrowserPublicLifecycleController()

    def execute_strategy(
        self,
        *,
        mission_id: str,
        purpose: str,
        tab_plans: list[BrowserPublicTabPlan],
        event_bus: EventBus,
        allowed_domains: list[str] | None = None,
        resolver: DnsResolver | None = None,
        max_tabs: int = 4,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserMultitabStrategyResult:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser multitab event bus mission_id must match mission_id.")
        if not tab_plans:
            return self._reject(mission_id, "browser_multitab_strategy_empty", event_bus, phase)
        if len(tab_plans) > max_tabs:
            return self._reject(
                mission_id,
                "browser_multitab_strategy_exceeds_max_tabs",
                event_bus,
                phase,
                errors=[f"requested:{len(tab_plans)}", f"max:{max_tabs}"],
            )

        session_result = self.lifecycle.start_session(
            mission_id=mission_id,
            purpose=purpose,
            max_tabs=max_tabs,
            event_bus=event_bus,
            phase=phase,
        )
        if not session_result.accepted or session_result.session is None:
            return self._reject(mission_id, session_result.reason, event_bus, phase, errors=session_result.errors)

        opened_tabs: list[BrowserPublicTab] = []
        trace_refs = [session_result.trace_event_id] if session_result.trace_event_id else []
        for plan in tab_plans:
            opened = self.lifecycle.open_tab(
                session_id=session_result.session.id,
                url=plan.url,
                allowed_domains=allowed_domains,
                resolver=resolver,
                event_bus=event_bus,
                phase=phase,
            )
            if not opened.accepted or opened.tab is None:
                return self._reject(
                    mission_id,
                    opened.reason,
                    event_bus,
                    phase,
                    errors=opened.errors,
                    trace_refs=trace_refs,
                )
            opened_tabs.append(opened.tab)
            if opened.trace_event_id:
                trace_refs.append(opened.trace_event_id)

        event = event_bus.append(
            AgentEventType.BROWSER_MULTITAB_STRATEGY_EXECUTED,
            "Browser V2.5 public multi-tab strategy executed through stateless lifecycle controller.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "session_id": session_result.session.id,
                "tab_ids": [tab.id for tab in opened_tabs],
                "tab_count": len(opened_tabs),
                "max_tabs": max_tabs,
                "purposes": [plan.purpose for plan in tab_plans],
                "final_urls": [tab.current_url for tab in opened_tabs],
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
            trace_refs=trace_refs,
        )
        return BrowserMultitabStrategyResult(
            accepted=True,
            reason="browser_multitab_strategy_executed",
            mission_id=mission_id,
            session_id=session_result.session.id,
            tabs=opened_tabs,
            trace_event_id=event.id,
        )

    @staticmethod
    def _reject(
        mission_id: str,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
        *,
        errors: list[str] | None = None,
        trace_refs: list[str] | None = None,
    ) -> BrowserMultitabStrategyResult:
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED,
            "Browser V2.5 public multi-tab strategy rejected.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": "multitab_strategy",
                "reason": reason,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": "rejected",
                "errors": errors or [reason],
            },
            trace_refs=trace_refs or [],
        )
        return BrowserMultitabStrategyResult(
            accepted=False,
            reason=reason,
            mission_id=mission_id,
            trace_event_id=event.id,
            errors=errors or [reason],
        )
