"""Tests for the local server's routes.

Each test runs a real server on an ephemeral port against a stub provider, so
the checks cover the wiring rather than a mock of it.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from caracat_code.interface import resolve_config
from caracat_code.server import (
    ServerOptions,
    create_server,
    make_handler,
    public_config,
)
from caracat_code.workspace import Workspace

PROVIDER_KEY = "stub-key-123"
INDEX = b"<!doctype html><title>Caracat Code</title>"


class StubProvider(BaseHTTPRequestHandler):
    """A minimal OpenAI-compatible provider."""

    def log_message(self, *args: object) -> None:
        pass

    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {PROVIDER_KEY}"

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._authorized():
            self._json(401, {"error": "bad key"})
        elif self.path == "/v1/models":
            self._json(200, {"data": [{"id": "stub/model"}]})
        else:
            self._json(404, {"error": "no such path"})

    def do_POST(self) -> None:
        if not self._authorized():
            self._json(401, {"error": "bad key"})
            return
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "no such path"})
            return
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        chunk = {"choices": [{"delta": {"content": "hello"}}]}
        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


def serve(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def free_port() -> int:
    """A port nobody is listening on.

    resolve_config rejects port 0 on purpose -- for a person typing --port it is
    a mistake, not a wish for an ephemeral port -- so the test picks a real one.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def provider() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubProvider)
    serve(server)
    yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()
    server.server_close()


def start_interface(api_base: str, **kwargs: object) -> Iterator[str]:
    config = resolve_config(
        env={"CARACAT_API_KEY": PROVIDER_KEY}, api_base=api_base, port=free_port()
    )
    options = ServerOptions(config=config, index_html=INDEX, **kwargs)  # type: ignore[arg-type]
    server = create_server(options)
    serve(server)
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def interface(provider: str) -> Iterator[str]:
    yield from start_interface(provider, system_prompt="Be Caracat Code.")


def get(url: str, **headers: str):
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=10)


def post(url: str, payload: object):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(request, timeout=10)


# ---- serving the page and settings -------------------------------------


def test_the_page_is_served(interface: str) -> None:
    with get(f"{interface}/") as response:
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/html")
        assert b"Caracat Code" in response.read()


def test_the_settings_carry_the_personality(interface: str) -> None:
    with get(f"{interface}/api/config") as response:
        settings = json.loads(response.read())

    assert settings["default_system_prompt"] == "Be Caracat Code."
    assert settings["has_api_key"] is True


def test_the_settings_never_carry_the_key(interface: str) -> None:
    with get(f"{interface}/api/config") as response:
        body = response.read().decode()

    assert PROVIDER_KEY not in body
    assert "api_key" not in json.loads(body)


def test_public_config_without_a_personality() -> None:
    config = resolve_config(env={"CARACAT_API_KEY": "k"})

    settings = public_config(ServerOptions(config=config, index_html=b""))

    assert settings["default_system_prompt"] is None


# ---- proxying ----------------------------------------------------------


def test_models_are_fetched_from_the_provider(interface: str) -> None:
    with get(f"{interface}/api/models") as response:
        assert json.loads(response.read())["data"] == [{"id": "stub/model"}]


def test_chat_streams_the_response(interface: str) -> None:
    with post(
        f"{interface}/api/chat",
        {"model": "stub/model", "messages": [{"role": "user", "content": "hi"}]},
    ) as response:
        body = response.read().decode()

    assert "hello" in body
    assert "[DONE]" in body


def test_a_bad_key_is_translated_into_advice(provider: str) -> None:
    config = resolve_config(
        env={"CARACAT_API_KEY": "wrong"}, api_base=provider, port=free_port()
    )
    server = create_server(ServerOptions(config=config, index_html=INDEX))
    serve(server)
    base = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            get(f"{base}/api/models")
        assert caught.value.code == 401
        assert "CARACAT_API_KEY" in caught.value.read().decode()
    finally:
        server.shutdown()
        server.server_close()


# ---- refusals ----------------------------------------------------------


def test_an_unknown_path_is_refused(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{interface}/etc/passwd")

    assert caught.value.code == 404


def test_a_foreign_host_header_is_refused(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{interface}/api/config", Host="evil.example")

    assert caught.value.code == 403
    assert "Host" in caught.value.read().decode()


def test_an_invalid_chat_request_is_refused(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(f"{interface}/api/chat", {"messages": [{"role": "root", "content": "x"}]})

    assert caught.value.code == 400


def test_posting_to_an_unknown_path_is_refused(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(f"{interface}/api/nonexistent", {"anything": True})

    assert caught.value.code == 404


# ---- the shipped page --------------------------------------------------

INDEX_PATH = Path(__file__).resolve().parent.parent / "interface" / "index.html"


def test_the_page_wires_up_the_personality() -> None:
    """A later rewrite of the page must not drop this silently."""
    page = INDEX_PATH.read_text(encoding="utf-8")

    assert "default_system_prompt" in page
    assert "reset-system" in page
    # The guard that stops a reload from throwing away an edited prompt.
    assert 'store.get("system", null)' in page


def test_the_page_loads_nothing_from_outside() -> None:
    """No CDN, no font, no stylesheet, no image from anywhere else.

    The page does name a few addresses, and the distinction matters: a *load* is
    a dependency the page cannot work without, while the provider endpoint is
    something the person chooses and can change. So the loading mechanisms are
    forbidden outright, and every address that remains has to be one of the
    handful that is meant to be there.
    """
    page = INDEX_PATH.read_text(encoding="utf-8")

    for marker in ("//cdn", "<script src", "<link href", "@import", "url(http"):
        assert marker not in page, f"the page must not reference {marker!r}"

    allowed = {
        # the default provider, editable in the page
        "https://router.huggingface.co/v1",
        "http://localhost:*",  # a local runtime, permitted by the page's own CSP
        "http://127.0.0.1:*;",  # the same, as it appears in the CSP
    }
    found = set(re.findall(r"https?://[^\"' <>)]*", page))
    unexpected = sorted(found - allowed)
    assert not unexpected, f"unexpected addresses in the page: {unexpected}"


def test_the_page_declares_a_restrictive_policy() -> None:
    """The rule above is only a convention until the browser enforces it."""
    page = INDEX_PATH.read_text(encoding="utf-8")

    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page)
    assert policy, "the page must declare a Content Security Policy"
    directives = policy.group(1)

    assert "default-src 'none'" in directives
    # Scripts and styles are inline, so no external origin is permitted for
    # either. Anything a future edit pulls from a CDN fails visibly.
    assert "script-src 'unsafe-inline'" in directives
    assert "style-src 'unsafe-inline'" in directives
    assert "img-src data:" in directives


def test_the_model_filter_matches_word_by_word() -> None:
    """Typing "qwen coder next" has to find Qwen/Qwen3-Coder-Next.

    The identifier separates those words with a slash and dashes, never spaces,
    so matching the filter as one string finds nothing -- and an empty dropdown
    reads as a broken page rather than as a filter that missed.
    """
    page = INDEX_PATH.read_text(encoding="utf-8")

    assert "matchesFilter" in page
    assert "split(/[\\s,]+/)" in page, "the filter must be split into terms"


def test_an_empty_model_list_says_which_kind_of_empty() -> None:
    """No match and no list are different problems with different fixes.

    The reason lives outside the message thread on purpose: "New chat" clears
    the thread, and the dropdown is where someone looks when there is nothing
    to pick.
    """
    page = INDEX_PATH.read_text(encoding="utf-8")

    assert "modelLoadError" in page
    assert "no match for filter" in page
    assert "could not load models" in page


def test_the_page_works_without_a_server() -> None:
    """A static host has no server, so the page has to notice and adapt.

    Without this the hosted page would sit forever on 'could not reach the local
    server' -- and the three capabilities that need a server must not merely be
    hidden, they have to be gone.
    """
    page = INDEX_PATH.read_text(encoding="utf-8")

    assert "staticBackend" in page and "serverBackend" in page
    # A static host that answers unknown paths with index.html would otherwise
    # look like a working server.
    assert 'typeof cfg.api_base !== "string"' in page
    # The key is the visitor's own in that mode, so it must be sayable and
    # removable, and it must never travel in the clear.
    assert "forget-key" in page
    assert "The endpoint must use https" in page


# ---- project files -----------------------------------------------------

FAKE_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "leaky.py").write_text(f"TOKEN = '{FAKE_KEY}'\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("not yours\n", encoding="utf-8")
    return root


@pytest.fixture
def with_project(provider: str, project: Path) -> Iterator[str]:
    yield from start_interface(provider, workspace=Workspace.open(project))


def test_the_file_tree_is_served(with_project: str) -> None:
    with get(f"{with_project}/api/files") as response:
        payload = json.loads(response.read())

    paths = [entry["path"] for entry in payload["entries"]]
    assert "src/main.py" in paths
    assert ".env" not in paths


def test_a_project_file_is_served(with_project: str) -> None:
    with get(f"{with_project}/api/file?path=src/main.py") as response:
        payload = json.loads(response.read())

    assert payload["text"] == "print('hi')\n"


def test_a_file_holding_a_credential_is_refused_over_http(with_project: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{with_project}/api/file?path=leaky.py")

    body = caught.value.read().decode()
    assert caught.value.code == 403
    assert "line 1" in body
    assert FAKE_KEY not in body


@pytest.mark.parametrize(
    "query",
    [
        "../outside.txt",
        "%2e%2e%2foutside.txt",
        "src%2F..%2F..%2Foutside.txt",
        "/etc/passwd",
    ],
)
def test_escaping_the_project_over_http_is_refused(
    with_project: str, query: str
) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{with_project}/api/file?path={query}")

    assert caught.value.code == 400
    assert b"not yours" not in caught.value.read()


def test_a_credential_file_is_refused_by_name_over_http(with_project: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{with_project}/api/file?path=.env")

    assert caught.value.code == 400
    assert "never readable" in caught.value.read().decode()


def test_the_file_routes_explain_themselves_without_a_project(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{interface}/api/files")

    assert caught.value.code == 404
    assert "--project-dir" in caught.value.read().decode()


def test_the_settings_report_no_project_by_default(interface: str) -> None:
    with get(f"{interface}/api/config") as response:
        assert json.loads(response.read())["project_dir"] is None


# ---- running code ------------------------------------------------------


def test_code_runs_and_the_result_comes_back(interface: str) -> None:
    with post(f"{interface}/api/run", {"code": "print(6 * 7)"}) as response:
        result = json.loads(response.read())

    assert result["succeeded"] is True
    assert "42" in result["stdout"]
    assert result["exit_code"] == 0


def test_a_failing_program_reports_its_error(interface: str) -> None:
    with post(f"{interface}/api/run", {"code": "1 / 0"}) as response:
        result = json.loads(response.read())

    assert result["succeeded"] is False
    assert "ZeroDivisionError" in result["stderr"]


def test_a_run_can_be_given_a_project_file(with_project: str) -> None:
    with post(
        f"{with_project}/api/run",
        {"code": "print(open('main.py').read().strip())", "files": ["src/main.py"]},
    ) as response:
        result = json.loads(response.read())

    assert "print('hi')" in result["stdout"]


def test_a_run_cannot_reach_outside_the_project(with_project: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(
            f"{with_project}/api/run",
            {"code": "pass", "files": ["../outside.txt"]},
        )

    assert caught.value.code == 400
    assert "outside the project" in caught.value.read().decode()


def test_a_run_cannot_take_a_credential_file(with_project: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(f"{with_project}/api/run", {"code": "pass", "files": [".env"]})

    assert caught.value.code == 400
    assert "never readable" in caught.value.read().decode()


def test_the_run_route_refuses_a_body_without_code(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(f"{interface}/api/run", {"files": []})

    assert caught.value.code == 400
    assert "'code' must be a string" in caught.value.read().decode()


def test_running_code_is_unavailable_when_bound_outward(provider: str) -> None:
    """Not a flag that can be forgotten -- the route simply is not registered."""
    config = resolve_config(
        env={"CARACAT_API_KEY": PROVIDER_KEY},
        api_base=provider,
        host="0.0.0.0",  # binding outward is the point of this test
        port=free_port(),
    )
    options = ServerOptions(config=config, index_html=INDEX)

    assert public_config(options)["can_run_code"] is False
    assert "/api/run" not in _post_routes(options)


def _post_routes(options: ServerOptions) -> set[str]:
    """The POST routes a handler built from these options would expose."""
    handler = make_handler(options)
    instance = handler.__new__(handler)  # no socket, no request
    return set(instance._routes("POST"))


# ---- serving from a public address --------------------------------------


def test_a_public_server_accepts_its_public_host_name(provider: str) -> None:
    """Bound outward, the Host header is the deployment's own name.

    Keeping the localhost rule here would 403 every real request. The rule
    protects a local server from DNS rebinding; a public one is reached by its
    public name by design.
    """
    config = resolve_config(
        env={"CARACAT_API_KEY": PROVIDER_KEY},
        api_base=provider,
        host="0.0.0.0",  # what a container binds to
        port=free_port(),
    )
    server = create_server(ServerOptions(config=config, index_html=INDEX))
    serve(server)
    base = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with get(f"{base}/api/config", Host="caracat-code.hf.space") as response:
            assert response.status == 200
            assert json.loads(response.read())["can_run_code"] is False
    finally:
        server.shutdown()
        server.server_close()


def test_a_local_server_still_rejects_a_foreign_host(interface: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(f"{interface}/api/config", Host="evil.example")

    assert caught.value.code == 403
