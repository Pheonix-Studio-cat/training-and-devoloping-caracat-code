"""Fetching data from the web.

The project owner chose automatic fetching without a per-request confirmation.
That choice is honoured. What is *not* negotiable is where a fetch may go,
because that is a different question and a worse failure:

**Internal addresses are blocked.** Loopback, private ranges, link-local -- and
with it the cloud metadata address 169.254.169.254, which is how a fetch turns
into credential theft on a rented machine. Every redirect hop is re-checked,
because a public hostname redirecting to 127.0.0.1 is the standard way around a
naive check.

The reason this matters even without a confirmation step: a model's output is
not trusted input. A file the assistant read could contain text engineered to
produce a URL. Blocking internal targets removes the worst outcome; the visible
history in the interface covers the rest.

The API key is never attached to a fetch. Only ``http`` and ``https`` are
possible, responses are capped and timed, and non-text responses are refused
rather than pasted into a conversation as noise.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

__all__ = [
    "MAX_REDIRECTS",
    "MAX_RESPONSE_BYTES",
    "BlockedAddressError",
    "FetchError",
    "FetchResult",
    "fetch_url",
    "is_blocked_host",
]

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 20

TEXTUAL_TYPES = (
    "text/",
    "application/json",
    "application/xml",
    "application/xhtml",
    "application/javascript",
    "application/x-ndjson",
    "+json",
    "+xml",
)

BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localdomain", ".home.arpa")


class FetchError(ValueError):
    """Raised when a URL cannot be fetched."""


class BlockedAddressError(FetchError):
    """Raised when a URL points somewhere a fetch must not go."""


@dataclass(frozen=True)
class FetchResult:
    """A fetched document, capped and decoded."""

    url: str
    final_url: str
    status: int
    content_type: str
    text: str
    truncated: bool = False


def _addresses_for(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Every address the hostname resolves to.

    All of them are checked, not just the first: a name resolving to one public
    and one private address must not pass because the public one was checked.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise FetchError(f"{hostname} could not be resolved: {exc.strerror}") from exc

    addresses = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0]))
        except ValueError:  # pragma: no cover - getaddrinfo returned something odd
            continue
    if not addresses:
        raise FetchError(f"{hostname} resolved to no usable address")
    return addresses


def is_blocked_host(hostname: str) -> str | None:
    """Why this host must not be fetched, or ``None`` if it may be.

    Returning the reason rather than a boolean so the interface can say what
    happened instead of failing silently.
    """
    name = hostname.strip().lower().rstrip(".")
    if not name:
        return "the URL has no host"
    if name == "localhost" or name.endswith(BLOCKED_HOST_SUFFIXES):
        return f"{hostname} is a local name"

    for address in _addresses_for(name):
        if address.is_loopback:
            return f"{hostname} resolves to the loopback address {address}"
        # Checked before is_private, which is also true for link-local and
        # would otherwise swallow the more useful explanation.
        if address.is_link_local:
            return (
                f"{hostname} resolves to the link-local address {address}. On a "
                "rented machine that range serves instance credentials."
            )
        if address.is_private:
            return f"{hostname} resolves to the private address {address}"
        if address.is_reserved or address.is_multicast or address.is_unspecified:
            return f"{hostname} resolves to the reserved address {address}"
    return None


def _check(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise FetchError(
            f"only http and https can be fetched, got {parsed.scheme or 'no scheme'!r}"
        )
    if not parsed.hostname:
        raise FetchError(f"{url!r} has no host")

    reason = is_blocked_host(parsed.hostname)
    if reason is not None:
        raise BlockedAddressError(
            f"refused to fetch {url}: {reason}. Internal addresses stay blocked "
            "so that a URL from a model response cannot reach your own machines."
        )
    return urlunparse(parsed._replace(fragment="")), parsed.hostname


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Stops urllib following redirects, so each hop can be checked here."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_url(url: str, *, max_bytes: int = MAX_RESPONSE_BYTES) -> FetchResult:
    """Fetch ``url`` as text, following redirects and checking every hop.

    Raises:
        FetchError: If the URL is unusable, the response is not text, or the
            request fails.
        BlockedAddressError: If any hop points at an internal address.
    """
    current, _ = _check(url)
    opener = urllib.request.build_opener(_NoRedirects)
    seen = [current]

    for _ in range(MAX_REDIRECTS + 1):
        request = urllib.request.Request(
            current,
            headers={
                "User-Agent": "CaracatCode/0.1 (local assistant)",
                "Accept": "text/*, application/json;q=0.9, */*;q=0.1",
            },
            # No credentials of any kind: the provider key belongs to the
            # provider, and nothing else has been authorised.
        )
        try:
            response = opener.open(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise FetchError(f"{current} redirected without a target") from exc
                current, _ = _check(urllib.parse.urljoin(current, location))
                if current in seen:
                    raise FetchError(f"{url} redirects in a loop") from exc
                seen.append(current)
                continue
            raise FetchError(f"{current} returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise FetchError(f"{current} could not be reached: {exc.reason}") from exc

        with response:
            content_type = response.headers.get("Content-Type", "")
            if not any(marker in content_type.lower() for marker in TEXTUAL_TYPES):
                raise FetchError(
                    f"{current} returned {content_type or 'an unknown type'}, which "
                    "is not text. Binary responses are not pasted into a "
                    "conversation."
                )
            raw = response.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            text = raw[:max_bytes].decode("utf-8", "replace")
            return FetchResult(
                url=url,
                final_url=current,
                status=response.status,
                content_type=content_type,
                text=text,
                truncated=truncated,
            )

    raise FetchError(f"{url} redirected more than {MAX_REDIRECTS} times")
