"""Tests for fetching data from the web.

Fetching happens without a confirmation click, by the project owner's choice.
That makes where a fetch may go the only line of defence, so most of these tests
are attempts to cross it.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from caracat_code.fetch import (
    BlockedAddressError,
    FetchError,
    fetch_url,
    is_blocked_host,
)

# ---- what must never be reachable --------------------------------------


@pytest.mark.parametrize(
    "hostname",
    [
        "localhost",
        "127.0.0.1",
        "127.1.2.3",
        "::1",
        "10.0.0.5",
        "172.16.4.4",
        "192.168.1.1",
        "0.0.0.0",
        "printer.local",
        "wiki.internal",
        "box.home.arpa",
    ],
)
def test_internal_hosts_are_blocked(hostname: str) -> None:
    assert is_blocked_host(hostname) is not None


def test_the_cloud_metadata_address_is_called_out_by_name() -> None:
    reason = is_blocked_host("169.254.169.254")

    assert reason is not None
    assert "credentials" in reason


def test_a_trailing_dot_does_not_bypass_the_name_check() -> None:
    assert is_blocked_host("localhost.") is not None


def test_case_does_not_bypass_the_name_check() -> None:
    assert is_blocked_host("LocalHost") is not None


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.org/x",
        "gopher://example.org/x",
        "data:text/plain,hello",
        "//example.org/x",
    ],
)
def test_only_http_and_https_are_possible(url: str) -> None:
    with pytest.raises(FetchError, match="only http and https"):
        fetch_url(url)


def test_a_loopback_url_is_refused_with_the_reason() -> None:
    with pytest.raises(BlockedAddressError) as caught:
        fetch_url("http://127.0.0.1:8765/api/config")

    message = str(caught.value)
    assert "loopback" in message
    assert "cannot reach your own machines" in message


def test_a_url_without_a_host_is_refused() -> None:
    with pytest.raises(FetchError, match="no host"):
        fetch_url("http:///nowhere")


# ---- the ordinary case, against a local stub ---------------------------


class StubSite(BaseHTTPRequestHandler):
    """Serves a few shapes of response for the fetch tests."""

    def log_message(self, *args: object) -> None:
        pass

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/text":
            self._send(200, "text/plain; charset=utf-8", b"hello from the stub")
        elif self.path == "/json":
            self._send(200, "application/json", json.dumps({"ok": True}).encode())
        elif self.path == "/binary":
            self._send(200, "image/png", b"\x89PNG\r\n\x1a\n")
        elif self.path == "/big":
            self._send(200, "text/plain", b"x" * 5000)
        elif self.path == "/redirect-inside":
            self.send_response(302)
            self.send_header("Location", "/text")
            self.end_headers()
        elif self.path == "/auth-echo":
            got = self.headers.get("Authorization", "none")
            self._send(200, "text/plain", f"authorization: {got}".encode())
        else:
            self._send(404, "text/plain", b"not found")


@pytest.fixture
def site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubSite)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def unblocked(url: str, **kwargs: object):
    """Fetch a loopback stub, bypassing only the address check.

    The address rule is tested directly above; here the goal is the behaviour
    that follows a successful check, which needs a server we control.
    """
    import caracat_code.fetch as module

    original = module.is_blocked_host
    module.is_blocked_host = lambda hostname: None  # type: ignore[assignment]
    try:
        return fetch_url(url, **kwargs)  # type: ignore[arg-type]
    finally:
        module.is_blocked_host = original  # type: ignore[assignment]


def test_text_is_returned(site: str) -> None:
    result = unblocked(f"{site}/text")

    assert result.status == 200
    assert result.text == "hello from the stub"
    assert not result.truncated


def test_json_is_accepted_as_text(site: str) -> None:
    assert '"ok": true' in unblocked(f"{site}/json").text


def test_a_binary_response_is_refused(site: str) -> None:
    with pytest.raises(FetchError, match="not text"):
        unblocked(f"{site}/binary")


def test_a_long_response_is_capped(site: str) -> None:
    result = unblocked(f"{site}/big", max_bytes=100)

    assert result.truncated
    assert len(result.text) == 100


def test_a_redirect_is_followed(site: str) -> None:
    result = unblocked(f"{site}/redirect-inside")

    assert result.text == "hello from the stub"
    assert result.final_url.endswith("/text")


def test_an_http_error_is_reported(site: str) -> None:
    with pytest.raises(FetchError, match="HTTP 404"):
        unblocked(f"{site}/missing")


def test_no_credentials_are_attached(site: str) -> None:
    result = unblocked(f"{site}/auth-echo")

    assert "authorization: none" in result.text
