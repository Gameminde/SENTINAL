"""CueIdea adapter layer for Sentinel Control."""

from sentinel.cueidea_bridge.client import CueIdeaBridge, CueIdeaTransport, HttpCueIdeaTransport
from sentinel.cueidea_bridge.normalizer import (
    normalize_competitors_response,
    normalize_trends_response,
    normalize_validation_response,
    normalize_watchlist_response,
    normalize_wtp_response,
)
from sentinel.cueidea_bridge.schemas import Competitor, TrendSignal, ValidationResult, Watchlist

__all__ = [
    "Competitor",
    "CueIdeaBridge",
    "CueIdeaTransport",
    "HttpCueIdeaTransport",
    "TrendSignal",
    "ValidationResult",
    "Watchlist",
    "normalize_competitors_response",
    "normalize_trends_response",
    "normalize_validation_response",
    "normalize_watchlist_response",
    "normalize_wtp_response",
]

