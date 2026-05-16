from __future__ import annotations

import json
import re
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from pydantic import Field

from sentinel.shared.models import SentinelModel


class BrowserExtractionStrategy(StrEnum):
    READABILITY = "readability"
    SIMPLE_HTML = "simple_html"
    TEXT_PLAIN = "text_plain"
    JSON_TEXT = "json_text"
    FALLBACK = "fallback"


class ReadablePageExtraction(SentinelModel):
    title: str | None = None
    text: str = ""
    links: list[str] = Field(default_factory=list)
    strategy: BrowserExtractionStrategy
    source_quality_flags: list[str] = Field(default_factory=list)
    truncated: bool = False
    raw_chars_extracted: int = Field(default=0, ge=0)
    citation_quote: str | None = None
    citation_char_start: int | None = None
    citation_char_end: int | None = None


class ReadablePageExtractor:
    """Deterministic page extraction for read-only browser evidence."""

    def extract(self, *, final_url: str, content_type: str, body: str, max_chars: int) -> ReadablePageExtraction:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime == "text/plain":
            return self._text_plain(body, max_chars=max_chars)
        if mime in {"application/json", "application/ld+json", "text/json"}:
            return self._json_text(body, max_chars=max_chars)
        if mime in {"text/html", "application/xhtml+xml"} or "<html" in body.lower():
            return self._html(final_url=final_url, body=body, max_chars=max_chars)
        return self._fallback(body, max_chars=max_chars)

    def _text_plain(self, body: str, *, max_chars: int) -> ReadablePageExtraction:
        text = _collapse_text([body])
        return _build_extraction(
            title=None,
            text=text,
            links=[],
            strategy=BrowserExtractionStrategy.TEXT_PLAIN,
            max_chars=max_chars,
            base_flags=[],
        )

    def _json_text(self, body: str, *, max_chars: int) -> ReadablePageExtraction:
        flags: list[str] = []
        try:
            payload = json.loads(body)
            text = _collapse_text(_json_values(payload))
        except json.JSONDecodeError:
            text = _collapse_text([body])
            flags.append("json_parse_failed")
        return _build_extraction(
            title=None,
            text=text,
            links=[],
            strategy=BrowserExtractionStrategy.JSON_TEXT,
            max_chars=max_chars,
            base_flags=flags,
        )

    def _html(self, *, final_url: str, body: str, max_chars: int) -> ReadablePageExtraction:
        parser = _ReadableHtmlParser(final_url)
        parser.feed(body)
        parser.close()
        main_text = _collapse_text(parser.main_text)
        body_text = _collapse_text(parser.body_text)
        boilerplate_text = _collapse_text(parser.boilerplate_text)
        flags: list[str] = []
        strategy = BrowserExtractionStrategy.SIMPLE_HTML

        if _word_count(main_text) >= 12:
            text = main_text
            strategy = BrowserExtractionStrategy.READABILITY
        elif body_text:
            text = body_text
            if _word_count(boilerplate_text) > max(8, _word_count(body_text) // 2):
                flags.append("boilerplate_heavy")
        else:
            text = _strip_tags(body)
            flags.append("fallback_text_extraction")
            strategy = BrowserExtractionStrategy.FALLBACK

        return _build_extraction(
            title=parser.title,
            text=text,
            links=parser.links,
            strategy=strategy,
            max_chars=max_chars,
            base_flags=flags,
        )

    def _fallback(self, body: str, *, max_chars: int) -> ReadablePageExtraction:
        return _build_extraction(
            title=None,
            text=_collapse_text([_strip_tags(body)]),
            links=[],
            strategy=BrowserExtractionStrategy.FALLBACK,
            max_chars=max_chars,
            base_flags=["unsupported_mime_fallback"],
        )


class _ReadableHtmlParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str | None = None
        self.links: list[str] = []
        self.main_text: list[str] = []
        self.body_text: list[str] = []
        self.boilerplate_text: list[str] = []
        self._tag_stack: list[str] = []
        self._in_title = False
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        self._tag_stack.append(lowered)
        if lowered == "title":
            self._in_title = True
        if lowered in {"script", "style", "noscript", "template", "svg"}:
            self._hidden_depth += 1
        if lowered == "a":
            attributes = dict(attrs)
            href = attributes.get("href")
            if href:
                self.links.append(urljoin(self.base_url, href))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = False
        if lowered in {"script", "style", "noscript", "template", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index] == lowered:
                del self._tag_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._in_title:
            current = f"{self.title} {value}" if self.title else value
            self.title = _collapse_text([current])[:240]
            return
        if self._hidden_depth:
            return
        if self._in_boilerplate():
            self.boilerplate_text.append(value)
            return
        self.body_text.append(value)
        if self._in_main_content():
            self.main_text.append(value)

    def _in_main_content(self) -> bool:
        return any(tag in {"main", "article"} for tag in self._tag_stack)

    def _in_boilerplate(self) -> bool:
        return any(tag in {"nav", "footer", "header", "aside"} for tag in self._tag_stack)


def _build_extraction(
    *,
    title: str | None,
    text: str,
    links: list[str],
    strategy: BrowserExtractionStrategy,
    max_chars: int,
    base_flags: list[str],
) -> ReadablePageExtraction:
    normalized = _collapse_text([unescape(text)])
    raw_chars = len(normalized)
    truncated = raw_chars > max_chars
    if truncated:
        normalized = normalized[:max_chars].rstrip()
    flags = list(base_flags)
    word_count = _word_count(normalized)
    if not normalized:
        flags.append("empty_extraction")
    elif word_count < 12:
        flags.append("thin_content")
    if not title:
        flags.append("no_title")
    if truncated:
        flags.append("truncated")
    quote = normalized[:500] if normalized else None
    return ReadablePageExtraction(
        title=title,
        text=normalized,
        links=links,
        strategy=strategy,
        source_quality_flags=sorted(set(flags)),
        truncated=truncated,
        raw_chars_extracted=raw_chars,
        citation_quote=quote,
        citation_char_start=0 if quote else None,
        citation_char_end=len(quote) if quote else None,
    )


def _json_values(value: Any) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, (int, float, str)):
        text = str(value).strip()
        return [text] if text else []
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(_json_values(item))
        return output
    if isinstance(value, dict):
        output = []
        for item in value.values():
            output.extend(_json_values(item))
        return output
    return []


def _strip_tags(value: str) -> str:
    stripped = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    stripped = re.sub(r"<style[\s\S]*?</style>", " ", stripped, flags=re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return unescape(stripped)


def _collapse_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))
