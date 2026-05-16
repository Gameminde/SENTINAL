from __future__ import annotations

from sentinel.organs.browser.models import (
    BrowserPublicLifecycleReceipt,
    BrowserPublicLifecycleResult,
    BrowserPublicLifecycleStatus,
    BrowserPublicSession,
    BrowserPublicTab,
    PublicUrlDecision,
    PublicUrlDecisionStatus,
    PublicUrlPolicy,
)
from sentinel.organs.browser.url_guard import DnsResolver, PublicUrlGuard
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus


class BrowserPublicLifecycleController:
    """Audits public browser session/tab state without owning private browser state."""

    def __init__(self, *, url_guard: PublicUrlGuard | None = None) -> None:
        self.url_guard = url_guard or PublicUrlGuard()
        self.sessions: dict[str, BrowserPublicSession] = {}
        self.tabs: dict[str, BrowserPublicTab] = {}

    def start_session(
        self,
        *,
        mission_id: str,
        purpose: str,
        event_bus: EventBus,
        max_tabs: int = 8,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPublicLifecycleResult:
        self._require_mission(event_bus, mission_id)
        session = BrowserPublicSession(
            mission_id=mission_id,
            purpose=purpose,
            max_tabs=max_tabs,
        )
        receipt = BrowserPublicLifecycleReceipt(
            mission_id=mission_id,
            action="start_session",
            session_id=session.id,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_SESSION_STARTED,
            "Public browser lifecycle session started without private profile state.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "session_id": session.id,
                "purpose": session.purpose,
                "max_tabs": session.max_tabs,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": session.status.value,
            },
        )
        trace_refs = [event.id]
        session = session.model_copy(update={"trace_refs": trace_refs})
        receipt = receipt.model_copy(update={"trace_refs": trace_refs})
        self.sessions[session.id] = session
        return BrowserPublicLifecycleResult(
            accepted=True,
            status=BrowserPublicLifecycleStatus.ACTIVE,
            reason="browser_public_session_started",
            action="start_session",
            mission_id=mission_id,
            session=session,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def open_tab(
        self,
        *,
        session_id: str,
        url: str,
        event_bus: EventBus,
        allowed_domains: list[str] | None = None,
        resolver: DnsResolver | None = None,
        redirects: list[str] | None = None,
        max_redirects: int = 3,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPublicLifecycleResult:
        session = self.sessions.get(session_id)
        if session is None:
            return self._rejected(
                mission_id=event_bus.mission_id,
                action="open_tab",
                reason="browser_public_session_missing",
                session_id=session_id,
                event_bus=event_bus,
                phase=phase,
            )
        self._require_mission(event_bus, session.mission_id)
        if session.status != BrowserPublicLifecycleStatus.ACTIVE:
            return self._rejected(
                mission_id=session.mission_id,
                action="open_tab",
                reason="browser_public_session_closed",
                session_id=session_id,
                event_bus=event_bus,
                phase=phase,
            )
        if self._active_tab_count(session_id) >= session.max_tabs:
            return self._rejected(
                mission_id=session.mission_id,
                action="open_tab",
                reason="browser_public_tab_limit_reached",
                session_id=session_id,
                event_bus=event_bus,
                phase=phase,
                errors=[f"max_tabs:{session.max_tabs}"],
            )

        decision, url_event = self._classify_url(
            url=url,
            event_bus=event_bus,
            allowed_domains=allowed_domains,
            resolver=resolver,
            redirects=redirects,
            max_redirects=max_redirects,
            phase=phase,
        )
        if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
            return self._rejected(
                mission_id=session.mission_id,
                action="open_tab",
                reason=decision.reason,
                session_id=session_id,
                url_event_id=url_event.id,
                event_bus=event_bus,
                phase=phase,
                errors=decision.errors,
            )

        tab = BrowserPublicTab(
            session_id=session.id,
            mission_id=session.mission_id,
            current_url=decision.final_url,
            current_url_policy_trace_id=url_event.id,
        )
        trace_refs = [*session.trace_refs, url_event.id]
        receipt = BrowserPublicLifecycleReceipt(
            mission_id=session.mission_id,
            action="open_tab",
            session_id=session.id,
            tab_id=tab.id,
            final_url=decision.final_url,
            url_policy_trace_id=url_event.id,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_TAB_OPENED,
            "Public browser tab opened in stateless lifecycle ledger.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "session_id": session.id,
                "tab_id": tab.id,
                "final_url": decision.final_url,
                "url_policy_trace_id": url_event.id,
                "navigation_count": tab.navigation_count,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": tab.status.value,
            },
            trace_refs=trace_refs,
        )
        tab_refs = [*trace_refs, event.id]
        tab = tab.model_copy(update={"opener_trace_id": event.id, "trace_refs": tab_refs})
        receipt = receipt.model_copy(update={"trace_refs": tab_refs})
        self.tabs[tab.id] = tab
        return BrowserPublicLifecycleResult(
            accepted=True,
            status=BrowserPublicLifecycleStatus.ACTIVE,
            reason="browser_public_tab_opened",
            action="open_tab",
            mission_id=session.mission_id,
            session=session,
            tab=tab,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def navigate_tab(
        self,
        *,
        session_id: str,
        tab_id: str,
        url: str,
        event_bus: EventBus,
        allowed_domains: list[str] | None = None,
        resolver: DnsResolver | None = None,
        redirects: list[str] | None = None,
        max_redirects: int = 3,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPublicLifecycleResult:
        session = self.sessions.get(session_id)
        tab = self.tabs.get(tab_id)
        validation = self._active_session_tab_error(session, tab, session_id=session_id, tab_id=tab_id)
        if validation is not None:
            return self._rejected(
                mission_id=session.mission_id if session else event_bus.mission_id,
                action="navigate_tab",
                reason=validation,
                session_id=session_id,
                tab_id=tab_id,
                event_bus=event_bus,
                phase=phase,
            )
        assert session is not None
        assert tab is not None
        self._require_mission(event_bus, session.mission_id)

        decision, url_event = self._classify_url(
            url=url,
            event_bus=event_bus,
            allowed_domains=allowed_domains,
            resolver=resolver,
            redirects=redirects,
            max_redirects=max_redirects,
            phase=phase,
        )
        if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
            return self._rejected(
                mission_id=session.mission_id,
                action="navigate_tab",
                reason=decision.reason,
                session_id=session_id,
                tab_id=tab_id,
                url_event_id=url_event.id,
                event_bus=event_bus,
                phase=phase,
                errors=decision.errors,
            )

        previous_url = tab.current_url
        next_count = tab.navigation_count + 1
        trace_refs = [*session.trace_refs, *tab.trace_refs, url_event.id]
        receipt = BrowserPublicLifecycleReceipt(
            mission_id=session.mission_id,
            action="navigate_tab",
            session_id=session.id,
            tab_id=tab.id,
            final_url=decision.final_url,
            url_policy_trace_id=url_event.id,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED,
            "Public browser tab navigation recorded with fresh URL policy proof.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "session_id": session.id,
                "tab_id": tab.id,
                "previous_url": previous_url,
                "final_url": decision.final_url,
                "url_policy_trace_id": url_event.id,
                "navigation_count": next_count,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": BrowserPublicLifecycleStatus.ACTIVE.value,
            },
            trace_refs=trace_refs,
        )
        tab_refs = [*trace_refs, event.id]
        updated_tab = tab.model_copy(
            update={
                "current_url": decision.final_url,
                "current_url_policy_trace_id": url_event.id,
                "navigation_count": next_count,
                "trace_refs": tab_refs,
            }
        )
        receipt = receipt.model_copy(update={"trace_refs": tab_refs})
        self.tabs[tab.id] = updated_tab
        return BrowserPublicLifecycleResult(
            accepted=True,
            status=BrowserPublicLifecycleStatus.ACTIVE,
            reason="browser_public_tab_navigated",
            action="navigate_tab",
            mission_id=session.mission_id,
            session=session,
            tab=updated_tab,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def close_tab(
        self,
        *,
        session_id: str,
        tab_id: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPublicLifecycleResult:
        session = self.sessions.get(session_id)
        tab = self.tabs.get(tab_id)
        validation = self._active_session_tab_error(session, tab, session_id=session_id, tab_id=tab_id)
        if validation is not None:
            return self._rejected(
                mission_id=session.mission_id if session else event_bus.mission_id,
                action="close_tab",
                reason=validation,
                session_id=session_id,
                tab_id=tab_id,
                event_bus=event_bus,
                phase=phase,
            )
        assert session is not None
        assert tab is not None
        self._require_mission(event_bus, session.mission_id)
        trace_refs = [*session.trace_refs, *tab.trace_refs]
        receipt = BrowserPublicLifecycleReceipt(
            mission_id=session.mission_id,
            action="close_tab",
            session_id=session.id,
            tab_id=tab.id,
            final_url=tab.current_url,
            url_policy_trace_id=tab.current_url_policy_trace_id,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_TAB_CLOSED,
            "Public browser tab closed in lifecycle ledger.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "session_id": session.id,
                "tab_id": tab.id,
                "final_url": tab.current_url,
                "url_policy_trace_id": tab.current_url_policy_trace_id,
                "navigation_count": tab.navigation_count,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": BrowserPublicLifecycleStatus.CLOSED.value,
            },
            trace_refs=trace_refs,
        )
        tab_refs = [*trace_refs, event.id]
        closed_tab = tab.model_copy(update={"status": BrowserPublicLifecycleStatus.CLOSED, "trace_refs": tab_refs})
        receipt = receipt.model_copy(update={"trace_refs": tab_refs})
        self.tabs[tab.id] = closed_tab
        return BrowserPublicLifecycleResult(
            accepted=True,
            status=BrowserPublicLifecycleStatus.CLOSED,
            reason="browser_public_tab_closed",
            action="close_tab",
            mission_id=session.mission_id,
            session=session,
            tab=closed_tab,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def close_session(
        self,
        *,
        session_id: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPublicLifecycleResult:
        session = self.sessions.get(session_id)
        if session is None:
            return self._rejected(
                mission_id=event_bus.mission_id,
                action="close_session",
                reason="browser_public_session_missing",
                session_id=session_id,
                event_bus=event_bus,
                phase=phase,
            )
        self._require_mission(event_bus, session.mission_id)
        if session.status != BrowserPublicLifecycleStatus.ACTIVE:
            return self._rejected(
                mission_id=session.mission_id,
                action="close_session",
                reason="browser_public_session_closed",
                session_id=session_id,
                event_bus=event_bus,
                phase=phase,
            )
        session_tabs = [tab for tab in self.tabs.values() if tab.session_id == session.id]
        active_tab_ids = sorted(tab.id for tab in session_tabs if tab.status == BrowserPublicLifecycleStatus.ACTIVE)
        trace_refs = [*session.trace_refs, *(ref for tab in session_tabs for ref in tab.trace_refs)]
        receipt = BrowserPublicLifecycleReceipt(
            mission_id=session.mission_id,
            action="close_session",
            session_id=session.id,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED,
            "Public browser lifecycle session closed and active tabs released.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "session_id": session.id,
                "closed_tab_ids": active_tab_ids,
                "tab_count": len(session_tabs),
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": BrowserPublicLifecycleStatus.CLOSED.value,
            },
            trace_refs=trace_refs,
        )
        all_refs = [*trace_refs, event.id]
        closed_session = session.model_copy(update={"status": BrowserPublicLifecycleStatus.CLOSED, "trace_refs": all_refs})
        receipt = receipt.model_copy(update={"trace_refs": all_refs})
        self.sessions[session.id] = closed_session
        for tab in session_tabs:
            if tab.status == BrowserPublicLifecycleStatus.ACTIVE:
                self.tabs[tab.id] = tab.model_copy(
                    update={"status": BrowserPublicLifecycleStatus.CLOSED, "trace_refs": [*tab.trace_refs, event.id]}
                )
        return BrowserPublicLifecycleResult(
            accepted=True,
            status=BrowserPublicLifecycleStatus.CLOSED,
            reason="browser_public_session_closed",
            action="close_session",
            mission_id=session.mission_id,
            session=closed_session,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def _classify_url(
        self,
        *,
        url: str,
        event_bus: EventBus,
        allowed_domains: list[str] | None,
        resolver: DnsResolver | None,
        redirects: list[str] | None,
        max_redirects: int,
        phase: AgentPhase,
    ) -> tuple[PublicUrlDecision, object]:
        policy = PublicUrlPolicy(
            allowed_schemes=["https"],
            allowed_domains=allowed_domains or [],
            max_redirects=max_redirects,
            require_dns_resolution=True,
        )
        decision = self.url_guard.evaluate(url, policy=policy, resolver=resolver, redirects=redirects or [])
        return decision, self._emit_url_decision(event_bus, decision, phase)

    @staticmethod
    def _emit_url_decision(event_bus: EventBus, decision: PublicUrlDecision, phase: AgentPhase):
        return event_bus.append(
            AgentEventType.BROWSER_URL_CLASSIFIED,
            "Browser URL classified before public lifecycle state changes.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "url_decision_id": decision.id,
                "status": decision.status,
                "reason": decision.reason,
                "original_url": decision.original_url,
                "final_url": decision.final_url,
                "host": decision.host,
                "resolved_addresses": decision.resolved_addresses,
                "redirect_chain": decision.redirect_chain,
                "errors": decision.errors,
            },
        )

    def _active_tab_count(self, session_id: str) -> int:
        return sum(
            1
            for tab in self.tabs.values()
            if tab.session_id == session_id and tab.status == BrowserPublicLifecycleStatus.ACTIVE
        )

    @staticmethod
    def _active_session_tab_error(
        session: BrowserPublicSession | None,
        tab: BrowserPublicTab | None,
        *,
        session_id: str,
        tab_id: str,
    ) -> str | None:
        if session is None:
            return "browser_public_session_missing"
        if session.status != BrowserPublicLifecycleStatus.ACTIVE:
            return "browser_public_session_closed"
        if tab is None:
            return "browser_public_tab_missing"
        if tab.session_id != session_id:
            return "browser_public_tab_session_mismatch"
        if tab.id != tab_id:
            return "browser_public_tab_id_mismatch"
        if tab.status != BrowserPublicLifecycleStatus.ACTIVE:
            return "browser_public_tab_closed"
        return None

    @staticmethod
    def _require_mission(event_bus: EventBus, mission_id: str) -> None:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser public lifecycle event bus mission_id must match request mission_id.")

    @staticmethod
    def _rejected(
        *,
        mission_id: str,
        action: str,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
        session_id: str | None = None,
        tab_id: str | None = None,
        url_event_id: str | None = None,
        errors: list[str] | None = None,
    ) -> BrowserPublicLifecycleResult:
        trace_refs = [url_event_id] if url_event_id else []
        event = event_bus.append(
            AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED,
            "Public browser lifecycle change rejected before state was accepted.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": action,
                "reason": reason,
                "session_id": session_id,
                "tab_id": tab_id,
                "url_policy_trace_id": url_event_id,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "status": BrowserPublicLifecycleStatus.REJECTED.value,
                "errors": errors or [],
            },
            trace_refs=trace_refs,
        )
        return BrowserPublicLifecycleResult(
            accepted=False,
            status=BrowserPublicLifecycleStatus.REJECTED,
            reason=reason,
            action=action,
            mission_id=mission_id,
            trace_event_id=event.id,
            errors=errors or [],
        )
