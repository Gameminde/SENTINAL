from __future__ import annotations

import ipaddress
import string
from collections.abc import Callable, Iterable
from urllib.parse import quote, unquote, urlsplit, urlunsplit, urljoin

from sentinel.organs.browser.models import PublicUrlDecision, PublicUrlDecisionStatus, PublicUrlPolicy


DnsResolver = Callable[[str], Iterable[str]]

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
)


class PublicUrlGuard:
    """Classifies candidate public URLs without opening a browser or network socket."""

    def evaluate(
        self,
        url: str,
        *,
        policy: PublicUrlPolicy | None = None,
        resolver: DnsResolver | None = None,
        redirects: Iterable[str] | None = None,
    ) -> PublicUrlDecision:
        active_policy = policy or PublicUrlPolicy()
        redirect_list = list(redirects or [])
        if len(redirect_list) > active_policy.max_redirects:
            return PublicUrlDecision(
                status=PublicUrlDecisionStatus.BLOCKED,
                reason="too_many_redirects",
                original_url=url,
                redirect_chain=redirect_list,
                errors=[f"redirect_count:{len(redirect_list)}"],
            )

        chain: list[str] = []
        current_url = url
        seen: set[str] = set()
        final_decision: PublicUrlDecision | None = None

        for index, location in enumerate([url, *redirect_list]):
            if index == 0:
                current_url = location
            else:
                current_url = urljoin(current_url, location)

            decision = self._evaluate_single(current_url, active_policy, resolver)
            if decision.normalized_url:
                current_url = decision.normalized_url
                if current_url in seen:
                    return self._copy_with_chain(
                        decision,
                        status=PublicUrlDecisionStatus.BLOCKED,
                        reason="redirect_loop_detected",
                        chain=chain,
                        errors=[*decision.errors, f"loop_url:{current_url}"],
                    )
                seen.add(current_url)
                chain.append(current_url)

            if decision.status != PublicUrlDecisionStatus.ALLOWED:
                return self._copy_with_chain(decision, chain=chain)
            final_decision = decision

        if final_decision is None:
            return PublicUrlDecision(
                status=PublicUrlDecisionStatus.BLOCKED,
                reason="invalid_url",
                original_url=url,
                errors=["empty_evaluation"],
            )

        return self._copy_with_chain(final_decision, chain=chain, final_url=chain[-1] if chain else final_decision.normalized_url)

    def _evaluate_single(
        self,
        url: str,
        policy: PublicUrlPolicy,
        resolver: DnsResolver | None,
    ) -> PublicUrlDecision:
        raw_input = str(url or "")
        if self._contains_unsafe_characters(raw_input):
            return self._blocked("unsafe_url_characters", raw_input)
        raw_url = raw_input.strip()
        try:
            parsed = urlsplit(raw_url)
        except ValueError as exc:
            return self._blocked("invalid_url", raw_url, errors=[str(exc)])

        if not parsed.scheme:
            return self._blocked("invalid_url", raw_url, errors=["missing_scheme"])
        scheme = parsed.scheme.lower()
        if scheme not in {value.lower() for value in policy.allowed_schemes}:
            return self._blocked("unsupported_scheme", raw_url, errors=[f"scheme:{scheme}"])
        if not parsed.hostname:
            return self._blocked("hostname_required", raw_url)
        if parsed.username or parsed.password:
            return self._blocked("userinfo_not_allowed", raw_url)
        try:
            port = parsed.port
        except ValueError as exc:
            return self._blocked("invalid_port", raw_url, errors=[str(exc)])

        try:
            host = self._normalize_host(parsed.hostname)
        except UnicodeError as exc:
            return self._blocked("invalid_hostname", raw_url, errors=[str(exc)])
        normalized_url = self._normalize_url(parsed, scheme, host, port)
        if self._is_blocked_hostname(host):
            return self._blocked("blocked_hostname", raw_url, normalized_url=normalized_url, host=host)
        if self._looks_like_obfuscated_ip(host):
            return self._blocked("obfuscated_ip_literal_not_allowed", raw_url, normalized_url=normalized_url, host=host)

        literal_ip = self._parse_ip(host)
        if literal_ip is not None:
            effective_ip = self._effective_ip(literal_ip)
            if not effective_ip.is_global:
                return self._blocked(
                    "private_or_internal_ip",
                    raw_url,
                    normalized_url=normalized_url,
                    host=host,
                    resolved_addresses=[str(literal_ip)],
                )
        if not self._domain_allowed(host, policy.allowed_domains):
            return PublicUrlDecision(
                status=PublicUrlDecisionStatus.UNAVAILABLE,
                reason="domain_not_allowed",
                original_url=raw_url,
                normalized_url=normalized_url,
                host=host,
                errors=[f"host:{host}"],
            )
        if literal_ip is not None:
            return PublicUrlDecision(
                status=PublicUrlDecisionStatus.ALLOWED,
                reason="allowed_public_url",
                original_url=raw_url,
                normalized_url=normalized_url,
                final_url=normalized_url,
                host=host,
                resolved_addresses=[str(literal_ip)],
            )

        if policy.require_dns_resolution and resolver is None:
            return self._blocked("dns_resolution_required", raw_url, normalized_url=normalized_url, host=host)

        resolved_addresses: list[str] = []
        if resolver is not None:
            try:
                resolved_addresses = [str(value) for value in resolver(host)]
            except Exception as exc:  # noqa: BLE001 - policy decision must capture resolver failure deterministically.
                return self._blocked("dns_resolution_failed", raw_url, normalized_url=normalized_url, host=host, errors=[str(exc)])
            if policy.require_dns_resolution and not resolved_addresses:
                return self._blocked("dns_resolution_empty", raw_url, normalized_url=normalized_url, host=host)
            blocked = self._first_non_public_address(resolved_addresses)
            if blocked is not None:
                return self._blocked(
                    "dns_resolution_private_or_internal",
                    raw_url,
                    normalized_url=normalized_url,
                    host=host,
                    resolved_addresses=resolved_addresses,
                    errors=[f"address:{blocked}"],
                )

        return PublicUrlDecision(
            status=PublicUrlDecisionStatus.ALLOWED,
            reason="allowed_public_url",
            original_url=raw_url,
            normalized_url=normalized_url,
            final_url=normalized_url,
            host=host,
            resolved_addresses=resolved_addresses,
        )

    @staticmethod
    def _blocked(
        reason: str,
        original_url: str,
        *,
        normalized_url: str | None = None,
        host: str | None = None,
        resolved_addresses: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> PublicUrlDecision:
        return PublicUrlDecision(
            status=PublicUrlDecisionStatus.BLOCKED,
            reason=reason,
            original_url=original_url,
            normalized_url=normalized_url,
            host=host,
            resolved_addresses=resolved_addresses or [],
            errors=errors or [],
        )

    @staticmethod
    def _copy_with_chain(
        decision: PublicUrlDecision,
        *,
        status: PublicUrlDecisionStatus | None = None,
        reason: str | None = None,
        chain: list[str],
        final_url: str | None = None,
        errors: list[str] | None = None,
    ) -> PublicUrlDecision:
        return decision.model_copy(
            update={
                "status": status or decision.status,
                "reason": reason or decision.reason,
                "redirect_chain": chain,
                "final_url": final_url or decision.final_url,
                "errors": errors or decision.errors,
            }
        )

    @staticmethod
    def _normalize_host(hostname: str) -> str:
        return hostname.rstrip(".").encode("idna").decode("ascii").lower()

    @staticmethod
    def _contains_unsafe_characters(url: str) -> bool:
        return any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url)

    @staticmethod
    def _normalize_url(parsed, scheme: str, host: str, port: int | None) -> str:
        host_part = f"[{host}]" if ":" in host and PublicUrlGuard._parse_ip(host) is not None else host
        if port is not None and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            host_part = f"{host_part}:{port}"
        path = quote(unquote(parsed.path or "/"), safe="/:@")
        query = parsed.query
        return urlunsplit((scheme, host_part, path, query, ""))

    @staticmethod
    def _is_blocked_hostname(host: str) -> bool:
        return host in _BLOCKED_HOSTS or any(host.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES)

    @staticmethod
    def _looks_like_obfuscated_ip(host: str) -> bool:
        lowered = host.lower()
        if lowered.isdigit():
            return True
        if lowered.startswith("0x") and all(character in string.hexdigits for character in lowered[2:]):
            return True
        parts = lowered.split(".")
        if len(parts) != 4:
            return False
        if not all(part and (part.isdigit() or part.startswith("0x")) for part in parts):
            return False
        return any(part.startswith("0x") or (part.startswith("0") and len(part) > 1) for part in parts)

    @staticmethod
    def _domain_allowed(host: str, allowed_domains: list[str]) -> bool:
        if not allowed_domains:
            return True
        for raw_domain in allowed_domains:
            domain = raw_domain.strip().lower().rstrip(".")
            if not domain:
                continue
            if domain.startswith("*."):
                suffix = domain[1:]
                if host.endswith(suffix) and host != domain[2:]:
                    return True
            elif host == domain or host.endswith(f".{domain}"):
                return True
        return False

    @staticmethod
    def _parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return None

    @staticmethod
    def _effective_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            return address.ipv4_mapped
        return address

    def _first_non_public_address(self, addresses: list[str]) -> str | None:
        for raw_address in addresses:
            address = self._parse_ip(raw_address)
            if address is None:
                return raw_address
            if not self._effective_ip(address).is_global:
                return raw_address
        return None
