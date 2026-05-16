from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser

from sentinel.organs.browser.models import (
    BrowserAccessibilitySnapshot,
    BrowserRoleRef,
    BrowserRoleSnapshotStats,
)


INTERACTIVE_ROLES = {
    "button",
    "link",
    "textbox",
    "checkbox",
    "radio",
    "combobox",
    "listbox",
    "option",
    "searchbox",
    "slider",
    "spinbutton",
    "switch",
    "tab",
}
CONTENT_ROLES = {"heading", "img", "article", "main", "navigation", "region"}


class BrowserAccessibilitySnapshotBuilder:
    """Builds deterministic role snapshots from already-captured rendered HTML."""

    def build(self, *, html: str, text: str = "") -> BrowserAccessibilitySnapshot:
        parser = _RoleHtmlParser()
        parser.feed(html)
        parser.close()
        candidates = parser.candidates()
        key_counts = Counter((candidate.role, candidate.name or "") for candidate in candidates if candidate.has_ref)
        refs: dict[str, BrowserRoleRef] = {}
        lines: list[str] = []
        ref_index = 0
        nth_seen: Counter[tuple[str, str]] = Counter()

        for candidate in candidates:
            line = f"{'  ' * candidate.depth}- {candidate.role}"
            if candidate.name:
                line += f' "{candidate.name}"'
            if candidate.has_ref:
                ref_index += 1
                ref = f"e{ref_index}"
                key = (candidate.role, candidate.name or "")
                nth = nth_seen[key]
                nth_seen[key] += 1
                refs[ref] = BrowserRoleRef(
                    role=candidate.role,
                    name=candidate.name,
                    nth=nth if key_counts[key] > 1 else None,
                )
                line += f" [ref={ref}]"
                if key_counts[key] > 1 and nth > 0:
                    line += f" [nth={nth}]"
            lines.append(line)

        if not lines and text:
            first = _collapse(text)[:120]
            if first:
                lines.append(f'- document "{first}"')
        snapshot = "\n".join(lines) if lines else "(empty)"
        stats = BrowserRoleSnapshotStats(
            lines=len(snapshot.splitlines()) if snapshot else 0,
            chars=len(snapshot),
            refs=len(refs),
            interactive=sum(1 for ref in refs.values() if ref.role in INTERACTIVE_ROLES),
        )
        page_sha = hashlib.sha256((html or text).encode("utf-8")).hexdigest()
        snapshot_sha = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
        return BrowserAccessibilitySnapshot(
            snapshot=snapshot,
            refs=refs,
            stats=stats,
            snapshot_sha256=snapshot_sha,
            page_sha256=page_sha,
        )


@dataclass
class _RoleCandidate:
    role: str
    name: str | None
    depth: int
    has_ref: bool


@dataclass
class _OpenElement:
    tag: str
    role: str | None
    depth: int
    name_hint: str | None = None
    text: list[str] = field(default_factory=list)


class _RoleHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_OpenElement] = []
        self.closed: list[_RoleCandidate] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attributes = {key.lower(): value for key, value in attrs if key}
        if lowered in {"script", "style", "noscript", "template", "svg"}:
            self.hidden_depth += 1
        role = _role_for(lowered, attributes)
        name_hint = _name_hint(lowered, attributes)
        self.stack.append(_OpenElement(tag=lowered, role=role, depth=max(0, len(self.stack)), name_hint=name_hint))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "template", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == lowered:
                closing = self.stack[index]
                del self.stack[index:]
                self._close_element(closing)
                break

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        value = data.strip()
        if not value:
            return
        for element in self.stack:
            element.text.append(value)

    def candidates(self) -> list[_RoleCandidate]:
        while self.stack:
            self._close_element(self.stack.pop())
        return self.closed

    def _close_element(self, element: _OpenElement) -> None:
        if not element.role:
            return
        name = _collapse(" ".join([element.name_hint or "", *element.text]))[:160] or None
        has_ref = element.role in INTERACTIVE_ROLES or (element.role in CONTENT_ROLES and bool(name))
        self.closed.append(_RoleCandidate(role=element.role, name=name, depth=element.depth, has_ref=has_ref))


def _role_for(tag: str, attrs: dict[str, str | None]) -> str | None:
    explicit = (attrs.get("role") or "").strip().lower()
    if explicit:
        return explicit
    if tag == "a" and attrs.get("href"):
        return "link"
    if tag == "button":
        return "button"
    if tag == "textarea":
        return "textbox"
    if tag == "select":
        return "combobox"
    if tag == "option":
        return "option"
    if tag == "img":
        return "img"
    if tag == "main":
        return "main"
    if tag == "nav":
        return "navigation"
    if tag == "article":
        return "article"
    if tag == "section" and (attrs.get("aria-label") or attrs.get("aria-labelledby")):
        return "region"
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return "heading"
    if tag == "input":
        input_type = (attrs.get("type") or "text").lower()
        return {
            "button": "button",
            "submit": "button",
            "reset": "button",
            "checkbox": "checkbox",
            "radio": "radio",
            "search": "searchbox",
            "range": "slider",
            "number": "spinbutton",
        }.get(input_type, "textbox")
    return None


def _name_hint(tag: str, attrs: dict[str, str | None]) -> str | None:
    for key in ("aria-label", "title", "alt", "placeholder", "value", "name"):
        value = attrs.get(key)
        if value:
            return value
    if tag == "input":
        return attrs.get("id")
    return None


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
