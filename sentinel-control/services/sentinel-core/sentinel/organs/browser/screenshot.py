from __future__ import annotations

import struct
from collections.abc import Callable

from sentinel.organs.browser.models import BrowserScreenshotMetadata


BrowserScreenshotNormalizer = Callable[[bytes, BrowserScreenshotMetadata], bytes]


class BrowserScreenshotNormalizationError(RuntimeError):
    pass


def screenshot_metadata(data: bytes, *, max_side: int, max_bytes: int) -> BrowserScreenshotMetadata:
    image_format, width, height = _image_dimensions(data)
    warnings: list[str] = []
    if image_format == "unknown":
        warnings.append("unknown_image_format")
    if width is None or height is None:
        warnings.append("dimensions_unavailable")
    if width is not None and height is not None and max(width, height) > max_side:
        warnings.append("dimensions_exceed_max_side")
    if len(data) > max_bytes:
        warnings.append("bytes_exceed_max")
    return BrowserScreenshotMetadata(
        content_type=_content_type(image_format),
        format=image_format,
        bytes=len(data),
        width=width,
        height=height,
        max_side=max_side,
        max_bytes=max_bytes,
        normalized=False,
        warnings=warnings,
    )


def normalize_browser_screenshot(
    data: bytes,
    *,
    max_side: int,
    max_bytes: int,
    normalizer: BrowserScreenshotNormalizer | None = None,
) -> tuple[bytes, BrowserScreenshotMetadata]:
    metadata = screenshot_metadata(data, max_side=max_side, max_bytes=max_bytes)
    if not _needs_normalization(metadata):
        return data, metadata
    if normalizer is None:
        raise BrowserScreenshotNormalizationError(";".join(metadata.warnings))

    normalized = normalizer(data, metadata)
    normalized_metadata = screenshot_metadata(normalized, max_side=max_side, max_bytes=max_bytes)
    blocking_warnings = _blocking_warnings(normalized_metadata)
    if blocking_warnings:
        raise BrowserScreenshotNormalizationError(";".join(blocking_warnings))
    return normalized, normalized_metadata.model_copy(
        update={
            "normalized": True,
            "original_bytes": metadata.bytes,
            "original_width": metadata.width,
            "original_height": metadata.height,
            "normalization_strategy": "external_normalizer",
        }
    )


def _needs_normalization(metadata: BrowserScreenshotMetadata) -> bool:
    return bool(_blocking_warnings(metadata))


def _blocking_warnings(metadata: BrowserScreenshotMetadata) -> list[str]:
    return [
        warning
        for warning in metadata.warnings
        if warning in {"dimensions_exceed_max_side", "bytes_exceed_max"}
    ]


def _content_type(image_format: str) -> str:
    if image_format == "png":
        return "image/png"
    if image_format == "jpeg":
        return "image/jpeg"
    return "application/octet-stream"


def _image_dimensions(data: bytes) -> tuple[str, int | None, int | None]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "png", struct.unpack(">I", data[16:20])[0], struct.unpack(">I", data[20:24])[0]
    if data.startswith(b"\xff\xd8"):
        return _jpeg_dimensions(data)
    return "unknown", None, None


def _jpeg_dimensions(data: bytes) -> tuple[str, int | None, int | None]:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        length = struct.unpack(">H", data[index : index + 2])[0]
        if length < 2 or index + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3} and length >= 7:
            height = struct.unpack(">H", data[index + 3 : index + 5])[0]
            width = struct.unpack(">H", data[index + 5 : index + 7])[0]
            return "jpeg", width, height
        index += length
    return "jpeg", None, None
