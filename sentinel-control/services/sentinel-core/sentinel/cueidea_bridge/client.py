from __future__ import annotations

from typing import Any, Protocol

from sentinel.cueidea_bridge.normalizer import (
    normalize_competitors_response,
    normalize_trends_response,
    normalize_validation_response,
    normalize_watchlist_response,
    normalize_wtp_response,
)
from sentinel.cueidea_bridge.schemas import Competitor, TrendSignal, ValidationResult, Watchlist
from sentinel.shared.models import EvidenceItem


class CueIdeaTransport(Protocol):
    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    async def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class HttpCueIdeaTransport:
    def __init__(self, base_url: str, timeout: float = 30.0, headers: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return dict(response.json())

    async def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.post(f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return dict(response.json())


class CueIdeaBridge:
    def __init__(self, transport: CueIdeaTransport) -> None:
        self.transport = transport

    async def validate_idea(self, idea: str) -> ValidationResult:
        payload = await self.transport.post_json("/api/validate", {"idea": idea, "idea_text": idea})
        return normalize_validation_response(payload, idea=idea)

    async def get_competitors(self, idea: str) -> list[Competitor]:
        payload = await self.transport.post_json("/api/competitor-radar", {"idea": idea, "idea_text": idea})
        return normalize_competitors_response(payload)

    async def get_wtp_signals(self, idea: str) -> list[EvidenceItem]:
        payload = await self.transport.post_json("/api/intelligence", {"idea": idea, "mode": "wtp"})
        return normalize_wtp_response(payload)

    async def get_trends(self, idea: str) -> list[TrendSignal]:
        payload = await self.transport.get_json("/api/trend-signals", {"idea": idea})
        return normalize_trends_response(payload)

    async def create_watchlist(self, idea: str, competitors: list[str]) -> Watchlist:
        payload = await self.transport.post_json("/api/watchlist", {"idea": idea, "competitors": competitors})
        return normalize_watchlist_response(payload, idea=idea, competitors=competitors)

