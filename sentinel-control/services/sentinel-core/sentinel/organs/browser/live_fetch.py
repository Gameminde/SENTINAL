from __future__ import annotations

import gzip
import http.client as http_client
import ssl
import zlib
from collections.abc import Iterable
from urllib.parse import urlsplit

import httpx

from sentinel.organs.browser.evidence_adapter import BrowserFetchError
from sentinel.organs.browser.models import (
    BrowserConnectionProof,
    BrowserEvidenceFetchRequest,
    BrowserFetchedPage,
    PublicUrlDecision,
)


DEFAULT_BROWSER_FETCH_TIMEOUT_SECONDS = 10.0
DEFAULT_BROWSER_FETCH_USER_AGENT = "SentinelBrowserReadOnly/1.0"


class ReadOnlyHttpFetcher:
    """Public HTTP GET fetcher for Browser V1.

    It does not run JavaScript, does not follow redirects, does not keep a
    session for reuse, does not submit forms, and does not write artifacts.
    URL policy, evidence conversion, artifact capture, and receipts are handled
    by the browser evidence adapter.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_BROWSER_FETCH_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_BROWSER_FETCH_USER_AGENT,
        transport: httpx.BaseTransport | None = None,
        pin_connections: bool = True,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.transport = transport
        self.pin_connections = pin_connections

    def __call__(
        self,
        request: BrowserEvidenceFetchRequest,
        final_url: str,
        url_decision: PublicUrlDecision | None = None,
    ) -> BrowserFetchedPage:
        if self.transport is None and self.pin_connections and url_decision is not None and url_decision.resolved_addresses:
            return self._fetch_pinned(request, final_url, url_decision)
        headers = {
            "accept": "text/html, text/plain;q=0.9, application/xhtml+xml;q=0.8",
            "accept-encoding": "gzip, deflate, identity",
            "user-agent": self.user_agent,
        }
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=self.timeout_seconds,
                headers=headers,
                cookies={},
                transport=self.transport,
                trust_env=False,
            ) as client:
                with client.stream("GET", final_url) as response:
                    compressed_body = self._read_response_body(response, request.max_compressed_bytes)
                    body = self._decode_body(compressed_body, response.headers.get("content-encoding"))
                    if len(body) > request.max_bytes:
                        raise BrowserFetchError("browser_body_too_large")
                    return BrowserFetchedPage(
                        final_url=str(response.url),
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type", "application/octet-stream"),
                        body=body.decode(response.encoding or "utf-8", errors="replace"),
                        headers={
                            key.lower(): value
                            for key, value in response.headers.items()
                            if key.lower() in {"content-type", "content-length", "location"}
                        },
                        compressed_bytes_read=len(compressed_body),
                        uncompressed_bytes_read=len(body),
                        connection_proof=self._connection_proof(url_decision),
                    )
        except BrowserFetchError:
            raise
        except httpx.HTTPError as exc:
            raise BrowserFetchError(str(exc)) from exc

    def _fetch_pinned(
        self,
        request: BrowserEvidenceFetchRequest,
        final_url: str,
        url_decision: PublicUrlDecision,
    ) -> BrowserFetchedPage:
        parsed = urlsplit(final_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise BrowserFetchError("browser_pinned_fetch_invalid_url")
        approved_address = url_decision.resolved_addresses[0]
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        target = f"{path}?{parsed.query}" if parsed.query else path
        host_header = self._host_header(url_decision.host or parsed.hostname, port, parsed.scheme)
        request_headers = {
            "Accept": "text/html, text/plain;q=0.9, application/xhtml+xml;q=0.8",
            "Accept-Encoding": "gzip, deflate, identity",
            "Connection": "close",
            "Host": host_header,
            "User-Agent": self.user_agent,
        }

        connection: http_client.HTTPConnection | None = None
        try:
            if parsed.scheme == "https":
                connection = _PinnedHttpsConnection(
                    approved_address,
                    server_hostname=url_decision.host or parsed.hostname,
                    port=port,
                    timeout=self.timeout_seconds,
                    context=ssl.create_default_context(),
                )
            else:
                connection = http_client.HTTPConnection(approved_address, port=port, timeout=self.timeout_seconds)
            connection.putrequest("GET", target, skip_host=True, skip_accept_encoding=True)
            for key, value in request_headers.items():
                connection.putheader(key, value)
            connection.endheaders()
            response = connection.getresponse()
            compressed_body = response.read(request.max_compressed_bytes + 1)
            if len(compressed_body) > request.max_compressed_bytes:
                raise BrowserFetchError("browser_compressed_body_too_large")
            body = self._decode_body(compressed_body, response.getheader("content-encoding"))
            if len(body) > request.max_bytes:
                raise BrowserFetchError("browser_body_too_large")
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            return BrowserFetchedPage(
                final_url=final_url,
                status_code=response.status,
                content_type=response_headers.get("content-type", "application/octet-stream"),
                body=body.decode(_charset_from_content_type(response_headers.get("content-type")) or "utf-8", errors="replace"),
                headers={
                    key: value
                    for key, value in response_headers.items()
                    if key in {"content-type", "content-length", "location"}
                },
                compressed_bytes_read=len(compressed_body),
                uncompressed_bytes_read=len(body),
                connection_proof=BrowserConnectionProof(
                    host=url_decision.host or parsed.hostname,
                    approved_addresses=url_decision.resolved_addresses,
                    connected_address=approved_address,
                    pinned=True,
                    redirect_chain=url_decision.redirect_chain,
                ),
            )
        except BrowserFetchError:
            raise
        except (OSError, ssl.SSLError, http_client.HTTPException) as exc:
            raise BrowserFetchError(str(exc)) from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _read_limited(chunks: Iterable[bytes], max_bytes: int) -> bytes:
        collected = bytearray()
        for chunk in chunks:
            collected.extend(chunk)
            if len(collected) > max_bytes:
                raise BrowserFetchError("browser_compressed_body_too_large")
        return bytes(collected)

    @classmethod
    def _read_response_body(cls, response: httpx.Response, max_bytes: int) -> bytes:
        try:
            return cls._read_limited(response.iter_raw(), max_bytes)
        except httpx.StreamConsumed:
            content = response.content
            if len(content) > max_bytes:
                raise BrowserFetchError("browser_compressed_body_too_large")
            return content

    @staticmethod
    def _decode_body(body: bytes, content_encoding: str | None) -> bytes:
        encoding = (content_encoding or "identity").split(",", 1)[0].strip().lower()
        try:
            if encoding in {"", "identity"}:
                return body
            if encoding == "gzip":
                return gzip.decompress(body)
            if encoding == "deflate":
                return zlib.decompress(body)
        except (OSError, zlib.error) as exc:
            raise BrowserFetchError(f"browser_content_decode_failed:{encoding}") from exc
        raise BrowserFetchError(f"browser_content_encoding_not_supported:{encoding}")

    @staticmethod
    def _connection_proof(url_decision: PublicUrlDecision | None) -> BrowserConnectionProof | None:
        if url_decision is None or not url_decision.host:
            return None
        return BrowserConnectionProof(
            host=url_decision.host,
            approved_addresses=url_decision.resolved_addresses,
            connected_address=None,
            pinned=False,
            redirect_chain=url_decision.redirect_chain,
        )

    @staticmethod
    def _host_header(host: str, port: int, scheme: str) -> str:
        host_part = f"[{host}]" if ":" in host and not host.startswith("[") else host
        if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
            return host_part
        return f"{host_part}:{port}"


class _PinnedHttpsConnection(http_client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        *,
        server_hostname: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._server_hostname = server_hostname

    def connect(self) -> None:
        sock = self._create_connection((self.host, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(sock, server_hostname=self._server_hostname)


def _charset_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    for part in content_type.split(";")[1:]:
        name, _, value = part.strip().partition("=")
        if name.lower() == "charset" and value:
            return value.strip("\"'")
    return None
