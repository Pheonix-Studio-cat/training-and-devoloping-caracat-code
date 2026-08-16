#!/usr/bin/env python3
"""Serve the local Caracat Code chat interface.

Starts a small web server on your own machine that serves the page in
``interface/index.html`` and forwards chat requests to an OpenAI-compatible
provider. The API key stays in this process: the browser never receives it.

    export CARACAT_API_KEY='...'
    python scripts/serve_interface.py

Then open http://127.0.0.1:8765 in a browser.

Any OpenAI-compatible endpoint works, including local runtimes:

    python scripts/serve_interface.py --api-base http://localhost:11434/v1
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Allow running the script directly from a checkout, without installing.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from caracat_code.interface import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    LOCAL_HOSTS,
    ChatRequestError,
    InterfaceConfig,
    InterfaceConfigError,
    build_chat_payload,
    redact,
    resolve_config,
    upstream_url,
)

INDEX_PATH = Path(__file__).resolve().parent.parent / "interface" / "index.html"
MAX_REQUEST_BYTES = 4 * 1024 * 1024
UPSTREAM_TIMEOUT_SECONDS = 300


class InterfaceHandler(BaseHTTPRequestHandler):
    """Serves the page and forwards exactly two kinds of upstream request."""

    config: InterfaceConfig
    index_html: bytes
    server_version = "CaracatInterface/0.1"
    sys_version = ""

    # ---- helpers -------------------------------------------------------

    def log_message(self, format: str, *args: object) -> None:
        """Log without ever including headers or bodies."""
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1]}\n")

    def _host_is_trusted(self) -> bool:
        """Reject requests whose Host header is not this local server.

        Without this check a hostile web page could point a hostname it
        controls at 127.0.0.1 and have the browser drive this server.
        """
        host_header = self.headers.get("Host", "")
        hostname = host_header.rsplit(":", 1)[0].strip().lower()
        return hostname in LOCAL_HOSTS or hostname == self.config.host.lower()

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": redact(message, self.config.api_key)})

    def _read_body(self) -> object:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ChatRequestError("Content-Length is not a number") from exc
        if length <= 0:
            raise ChatRequestError("the request body is empty")
        if length > MAX_REQUEST_BYTES:
            raise ChatRequestError(
                f"the request body is {length} bytes, the limit is {MAX_REQUEST_BYTES}"
            )
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ChatRequestError(
                f"the request body is not valid JSON: {exc}"
            ) from exc

    def _upstream_request(self, path: str, payload: dict[str, object] | None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            upstream_url(self.config.api_base, path),
            data=data,
            method="POST" if data is not None else "GET",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
                if data is not None
                else "application/json",
            },
        )
        return urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS)

    def _upstream_failure(self, exc: Exception) -> tuple[int, str]:
        """Translate an upstream failure into a status and a safe message."""
        if isinstance(exc, urllib.error.HTTPError):
            detail = ""
            with contextlib.suppress(OSError):
                detail = exc.read().decode("utf-8", "replace")[:2000]
            if exc.code in (401, 403):
                return exc.code, (
                    "The provider rejected the API key. Check CARACAT_API_KEY "
                    "and that it is valid for this endpoint."
                )
            if exc.code == 404:
                return 404, (
                    "The provider does not know this endpoint or model. Check "
                    f"the API base URL ({self.config.api_base}) and the "
                    f"selected model. Response: {detail}"
                )
            return exc.code, f"The provider returned {exc.code}: {detail}"
        if isinstance(exc, urllib.error.URLError):
            return 502, f"Could not reach {self.config.api_base}: {exc.reason}"
        return 502, f"Upstream request failed: {exc}"

    # ---- routes --------------------------------------------------------

    def do_GET(self) -> None:
        if not self._host_is_trusted():
            self._send_error_json(403, "unexpected Host header")
            return

        route = self.path.split("?", 1)[0]
        if route == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.index_html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(self.index_html)
            return

        if route == "/api/config":
            self._send_json(200, self.config.public_settings())
            return

        if route == "/api/models":
            try:
                with self._upstream_request("models", None) as response:
                    body = response.read()
            except Exception as exc:
                status, message = self._upstream_failure(exc)
                self._send_error_json(status, message)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        self._send_error_json(404, f"unknown path {route!r}")

    def do_POST(self) -> None:
        if not self._host_is_trusted():
            self._send_error_json(403, "unexpected Host header")
            return

        if self.path.split("?", 1)[0] != "/api/chat":
            self._send_error_json(404, f"unknown path {self.path!r}")
            return

        try:
            payload = build_chat_payload(
                self._read_body(), default_model=self.config.model
            )
        except ChatRequestError as exc:
            self._send_error_json(400, str(exc))
            return

        try:
            upstream = self._upstream_request("chat/completions", payload)
        except Exception as exc:
            status, message = self._upstream_failure(exc)
            self._send_error_json(status, message)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            with upstream:
                for chunk in iter(lambda: upstream.read(1024), b""):
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser stopped the response; nothing to clean up


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the local Caracat Code chat interface.",
        epilog=(
            "The API key is read from CARACAT_API_KEY and is never sent to the "
            "browser. There is no flag for it on purpose: a key passed on the "
            "command line ends up in your shell history."
        ),
    )
    parser.add_argument(
        "--api-base",
        help=(
            "OpenAI-compatible base URL "
            f"(default: {DEFAULT_API_BASE}, or CARACAT_API_BASE)."
        ),
    )
    parser.add_argument(
        "--model",
        help="Model to preselect, e.g. a Qwen3-Coder-Next identifier from your "
        "provider. Can also be chosen in the interface.",
    )
    parser.add_argument("--host", help=f"Address to bind to (default: {DEFAULT_HOST}).")
    parser.add_argument(
        "--port", type=int, help=f"Port to listen on (default: {DEFAULT_PORT})."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = resolve_config(
            api_base=args.api_base,
            model=args.model,
            host=args.host,
            port=args.port,
        )
    except InterfaceConfigError as exc:
        print(f"Cannot start the interface:\n\n{exc}", file=sys.stderr)
        return 2

    if not INDEX_PATH.is_file():
        print(f"Interface page not found: {INDEX_PATH}", file=sys.stderr)
        return 2

    InterfaceHandler.config = config
    InterfaceHandler.index_html = INDEX_PATH.read_bytes()

    if not config.is_local_only:
        print(
            f"WARNING: binding to {config.host} makes this interface reachable "
            "from other machines. Anyone who can reach it can spend your API "
            "key. Use the default 127.0.0.1 unless you know you want this.",
            file=sys.stderr,
        )

    server = ThreadingHTTPServer((config.host, config.port), InterfaceHandler)
    print(f"Caracat Code interface: http://{config.host}:{config.port}")
    print(f"Provider: {config.api_base}")
    print(f"Model:    {config.model or '(choose one in the interface)'}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
