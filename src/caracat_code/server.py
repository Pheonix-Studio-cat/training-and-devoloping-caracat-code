"""The local HTTP server behind the Caracat Code interface.

This lives in the package rather than in ``scripts/serve_interface.py`` so that
routes can be tested directly. The script is a thin command-line wrapper around
:func:`create_server`.

What the server does and does not do is deliberate:

- it forwards to exactly the upstream paths in
  :data:`caracat_code.interface.ALLOWED_UPSTREAM_PATHS`, so it cannot be used as
  an open proxy;
- it validates every field of a chat request instead of passing it through;
- it rejects requests carrying a foreign ``Host`` header, which is what stops a
  hostile page from driving a server bound to localhost;
- the API key stays in this process and is redacted out of anything sent back.
"""

from __future__ import annotations

import contextlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from caracat_code.interface import (
    LOCAL_HOSTS,
    ChatRequestError,
    InterfaceConfig,
    build_chat_payload,
    redact,
    upstream_url,
)
from caracat_code.workspace import Workspace, WorkspaceError, WorkspaceSecretError

__all__ = [
    "MAX_REQUEST_BYTES",
    "UPSTREAM_TIMEOUT_SECONDS",
    "ServerOptions",
    "create_server",
    "make_handler",
    "public_config",
]

MAX_REQUEST_BYTES = 4 * 1024 * 1024
UPSTREAM_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class ServerOptions:
    """Everything the running server needs, assembled by the CLI."""

    config: InterfaceConfig
    index_html: bytes
    system_prompt: str | None = None
    workspace: Workspace | None = None


def public_config(options: ServerOptions) -> dict[str, object]:
    """The settings handed to the browser.

    Never includes the API key -- see
    :meth:`caracat_code.interface.InterfaceConfig.public_settings`.
    """
    return {
        **options.config.public_settings(),
        "default_system_prompt": options.system_prompt,
        "project_dir": str(options.workspace.root) if options.workspace else None,
    }


def make_handler(options: ServerOptions) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to ``options``.

    A factory rather than module-level state, so tests can run several servers
    with different settings in the same process.
    """

    class InterfaceHandler(BaseHTTPRequestHandler):
        server_version = "CaracatInterface/0.1"
        sys_version = ""

        # ---- plumbing --------------------------------------------------

        def log_message(self, format: str, *args: object) -> None:
            """Log the route and status only -- never headers or bodies."""
            sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1]}\n")

        def _host_is_trusted(self) -> bool:
            hostname = self.headers.get("Host", "").rsplit(":", 1)[0].strip().lower()
            return hostname in LOCAL_HOSTS or hostname == options.config.host.lower()

        def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def _send_json(self, status: int, payload: object) -> None:
            self._send_bytes(
                status,
                "application/json; charset=utf-8",
                json.dumps(payload).encode("utf-8"),
            )

        def _send_error_json(self, status: int, message: str) -> None:
            self._send_json(status, {"error": redact(message, options.config.api_key)})

        def _read_body(self) -> object:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ChatRequestError("Content-Length is not a number") from exc
            if length <= 0:
                raise ChatRequestError("the request body is empty")
            if length > MAX_REQUEST_BYTES:
                raise ChatRequestError(
                    f"the request body is {length} bytes, the limit is "
                    f"{MAX_REQUEST_BYTES}"
                )
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ChatRequestError(
                    f"the request body is not valid JSON: {exc}"
                ) from exc

        # ---- upstream --------------------------------------------------

        def _upstream_request(self, path: str, payload: dict[str, object] | None):
            data = json.dumps(payload).encode("utf-8") if payload is not None else None
            request = urllib.request.Request(
                upstream_url(options.config.api_base, path),
                data=data,
                method="POST" if data is not None else "GET",
                headers={
                    "Authorization": f"Bearer {options.config.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                    if data is not None
                    else "application/json",
                },
            )
            return urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS)

        def _upstream_failure(self, exc: Exception) -> tuple[int, str]:
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
                        f"the API base URL ({options.config.api_base}) and the "
                        f"selected model. Response: {detail}"
                    )
                return exc.code, f"The provider returned {exc.code}: {detail}"
            if isinstance(exc, urllib.error.URLError):
                return 502, f"Could not reach {options.config.api_base}: {exc.reason}"
            return 502, f"Upstream request failed: {exc}"

        # ---- routes ----------------------------------------------------

        def route_index(self) -> None:
            self._send_bytes(200, "text/html; charset=utf-8", options.index_html)

        def route_config(self) -> None:
            self._send_json(200, public_config(options))

        def route_models(self) -> None:
            try:
                with self._upstream_request("models", None) as response:
                    body = response.read()
            except Exception as exc:
                status, message = self._upstream_failure(exc)
                self._send_error_json(status, message)
                return
            self._send_bytes(200, "application/json; charset=utf-8", body)

        def _query(self, name: str) -> str:
            values = parse_qs(urlparse(self.path).query).get(name, [])
            return values[0] if values else ""

        def _workspace(self) -> Workspace | None:
            if options.workspace is None:
                self._send_error_json(
                    404,
                    "No project directory is open. Restart the server with "
                    "--project-dir <path> to let Caracat Code read your files.",
                )
                return None
            return options.workspace

        def route_files(self) -> None:
            workspace = self._workspace()
            if workspace is None:
                return
            entries = workspace.tree()
            self._send_json(
                200,
                {
                    "root": str(workspace.root),
                    "entries": [
                        {"path": e.path, "is_dir": e.is_dir, "size": e.size}
                        for e in entries
                    ],
                },
            )

        def route_file(self) -> None:
            workspace = self._workspace()
            if workspace is None:
                return
            try:
                content = workspace.read(self._query("path"))
            except WorkspaceSecretError as exc:
                # 403 rather than 400: the request was well formed, the content
                # is what makes it refusable.
                self._send_error_json(403, str(exc))
                return
            except WorkspaceError as exc:
                self._send_error_json(400, str(exc))
                return
            except OSError as exc:
                self._send_error_json(400, f"could not read the file: {exc}")
                return
            self._send_json(
                200,
                {"path": content.path, "text": content.text, "lines": content.lines},
            )

        def route_chat(self) -> None:
            try:
                payload = build_chat_payload(
                    self._read_body(), default_model=options.config.model
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
                pass  # the browser stopped listening; nothing to clean up

        # ---- dispatch --------------------------------------------------

        def _routes(self, method: str) -> dict[str, Callable[[], None]]:
            if method == "GET":
                return {
                    "/": self.route_index,
                    "/api/config": self.route_config,
                    "/api/models": self.route_models,
                    "/api/files": self.route_files,
                    "/api/file": self.route_file,
                }
            return {"/api/chat": self.route_chat}

        def _dispatch(self, method: str) -> None:
            if not self._host_is_trusted():
                self._send_error_json(403, "unexpected Host header")
                return
            route = self.path.split("?", 1)[0]
            handler = self._routes(method).get(route)
            if handler is None:
                self._send_error_json(404, f"unknown path {route!r}")
                return
            handler()

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

    return InterfaceHandler


def create_server(options: ServerOptions) -> ThreadingHTTPServer:
    """Create the HTTP server. Call ``serve_forever`` on the result to run it."""
    return ThreadingHTTPServer(
        (options.config.host, options.config.port), make_handler(options)
    )


def read_index(path: str | Path) -> bytes:
    """Read the interface page, with a clear error when it is missing."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"interface page not found: {source}")
    return source.read_bytes()
