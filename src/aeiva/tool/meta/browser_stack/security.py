from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

_DEFAULT_BLOCKED_CIDR_TEXT = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "::/128",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
)


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    text = raw.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _split_csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    values = []
    for token in raw.split(","):
        item = token.strip()
        if item:
            values.append(item.lower())
    return tuple(values)


def _normalize_roots(roots: Iterable[str]) -> tuple[Path, ...]:
    out = []
    seen: set[str] = set()
    for raw in roots:
        text = str(raw or "").strip()
        if not text:
            continue
        path = Path(text).expanduser().resolve()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return tuple(out)


def _parse_cidrs(items: Iterable[str]) -> tuple[IPNetwork, ...]:
    networks: list[IPNetwork] = []
    seen: set[str] = set()
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        try:
            network = ipaddress.ip_network(text, strict=False)
        except ValueError:
            continue
        key = str(network)
        if key in seen:
            continue
        seen.add(key)
        networks.append(network)
    return tuple(networks)


_DEFAULT_BLOCKED_NETWORKS = _parse_cidrs(_DEFAULT_BLOCKED_CIDR_TEXT)


def _host_matches_allowlist(host: str, allowlist: tuple[str, ...]) -> bool:
    if not allowlist:
        return True
    lowered = host.lower()
    for token in allowlist:
        if lowered == token:
            return True
        if lowered.endswith(f".{token}"):
            return True
    return False


def _is_local_host(host: str) -> bool:
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".local"):
        return True
    return False


def _parse_host_ip(host: str) -> Optional[IPAddress]:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _ip_in_blocked_cidrs(ip: IPAddress, blocked_cidrs: tuple[IPNetwork, ...]) -> bool:
    return any(ip in network for network in blocked_cidrs)


def _resolve_host_ips(host: str) -> tuple[IPAddress, ...]:
    resolved: list[IPAddress] = []
    seen: set[str] = set()
    for _, _, _, _, sockaddr in socket.getaddrinfo(host, None):
        if not sockaddr:
            continue
        candidate = str(sockaddr[0] or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            resolved.append(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return tuple(resolved)


def _is_path_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class BrowserSecurityPolicy:
    allow_evaluate: bool
    allow_private_network_requests: bool
    request_allowlist: tuple[str, ...]
    request_blocked_cidrs: tuple[IPNetwork, ...] = ()
    check_dns_private_hosts: bool = True
    dns_fail_closed: bool = False
    allow_any_upload_path: bool = False
    upload_roots: tuple[Path, ...] = ()

    @classmethod
    def from_env(cls) -> "BrowserSecurityPolicy":
        upload_roots_raw = _split_csv_env("AEIVA_BROWSER_UPLOAD_ROOTS")
        if upload_roots_raw:
            upload_roots = _normalize_roots(upload_roots_raw)
        else:
            upload_roots = _normalize_roots([str(Path.cwd()), str(Path.home())])
        request_blocked_cidrs = _parse_cidrs(_split_csv_env("AEIVA_BROWSER_REQUEST_BLOCKED_CIDRS"))
        return cls(
            allow_evaluate=_parse_bool_env("AEIVA_BROWSER_ALLOW_EVALUATE", False),
            allow_private_network_requests=_parse_bool_env(
                "AEIVA_BROWSER_ALLOW_PRIVATE_NETWORK_REQUESTS", False
            ),
            request_allowlist=_split_csv_env("AEIVA_BROWSER_REQUEST_ALLOWLIST"),
            request_blocked_cidrs=request_blocked_cidrs,
            check_dns_private_hosts=_parse_bool_env(
                "AEIVA_BROWSER_REQUEST_CHECK_DNS_PRIVATE",
                True,
            ),
            dns_fail_closed=_parse_bool_env("AEIVA_BROWSER_REQUEST_DNS_FAIL_CLOSED", False),
            allow_any_upload_path=_parse_bool_env("AEIVA_BROWSER_UPLOAD_ALLOW_ANY_PATH", False),
            upload_roots=upload_roots,
        )

    def validate_request_url(self, url: str) -> Tuple[bool, Optional[str]]:
        parsed = urlparse(str(url or "").strip())
        scheme = (parsed.scheme or "").lower()
        if scheme not in {"http", "https"}:
            return False, "Only http(s) URLs are allowed for browser request."

        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False, "Request URL must include a valid hostname."

        if not _host_matches_allowlist(host, self.request_allowlist):
            allowlist_text = ", ".join(self.request_allowlist)
            return (
                False,
                "Request URL host is outside AEIVA_BROWSER_REQUEST_ALLOWLIST "
                f"({allowlist_text}).",
            )

        if self.allow_private_network_requests:
            return True, None

        blocked_cidrs = self.request_blocked_cidrs or _DEFAULT_BLOCKED_NETWORKS

        if _is_local_host(host):
            return (
                False,
                "Private/local network targets are blocked. Set "
                "AEIVA_BROWSER_ALLOW_PRIVATE_NETWORK_REQUESTS=1 to override.",
            )

        host_ip = _parse_host_ip(host)
        if host_ip is not None and _ip_in_blocked_cidrs(host_ip, blocked_cidrs):
            return (
                False,
                "Private/local network targets are blocked. Set "
                "AEIVA_BROWSER_ALLOW_PRIVATE_NETWORK_REQUESTS=1 to override.",
            )

        if self.check_dns_private_hosts:
            try:
                resolved_ips = _resolve_host_ips(host)
            except OSError:
                if self.dns_fail_closed:
                    return (
                        False,
                        "DNS resolution failed for request host and policy is fail-closed "
                        "(AEIVA_BROWSER_REQUEST_DNS_FAIL_CLOSED=1).",
                    )
                resolved_ips = ()
            if not resolved_ips and self.dns_fail_closed:
                return (
                    False,
                    "DNS resolution produced no addresses for request host and policy is "
                    "fail-closed (AEIVA_BROWSER_REQUEST_DNS_FAIL_CLOSED=1).",
                )
            for resolved in resolved_ips:
                if _ip_in_blocked_cidrs(resolved, blocked_cidrs):
                    return (
                        False,
                        "Request host resolves to a private/local address "
                        f"({resolved}). Set "
                        "AEIVA_BROWSER_ALLOW_PRIVATE_NETWORK_REQUESTS=1 to override.",
                    )

        return True, None

    def resolve_upload_paths(self, paths: Iterable[str]) -> list[str]:
        resolved: list[Path] = []
        for raw_path in paths:
            text = str(raw_path or "").strip()
            if not text:
                continue
            resolved.append(Path(text).expanduser().resolve())
        if not resolved:
            raise ValueError("paths are required for upload operation")

        if self.allow_any_upload_path:
            return [str(path) for path in resolved]

        if not self.upload_roots:
            raise ValueError(
                "No upload roots configured. Set AEIVA_BROWSER_UPLOAD_ROOTS or "
                "AEIVA_BROWSER_UPLOAD_ALLOW_ANY_PATH=1."
            )

        denied: list[str] = []
        for path in resolved:
            if any(_is_path_within_root(path, root) for root in self.upload_roots):
                continue
            denied.append(str(path))
        if denied:
            roots = ", ".join(str(root) for root in self.upload_roots)
            raise ValueError(
                "Upload path blocked by policy: "
                + ", ".join(denied)
                + ". Allowed roots: "
                + roots
                + ". Set AEIVA_BROWSER_UPLOAD_ALLOW_ANY_PATH=1 to override."
            )

        return [str(path) for path in resolved]
