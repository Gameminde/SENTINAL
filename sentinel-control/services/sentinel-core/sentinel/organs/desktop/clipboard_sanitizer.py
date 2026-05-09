from __future__ import annotations

from sentinel.organs.desktop.screen_sanitizer import SanitizedDesktopContext, redact_secret_like_text


class ClipboardSanitizer:
    def sanitize(self, text: str) -> SanitizedDesktopContext:
        return redact_secret_like_text(text)
