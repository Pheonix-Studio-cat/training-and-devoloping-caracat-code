"""Tests for the local chat interface logic."""

from __future__ import annotations

import pytest

from caracat_code.interface import (
    DEFAULT_API_BASE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ChatRequestError,
    InterfaceConfigError,
    build_chat_payload,
    redact,
    resolve_config,
    upstream_url,
)

KEY = {"CARACAT_API_KEY": "test-key"}


def chat_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "model": "some/model",
        "messages": [{"role": "user", "content": "hello"}],
    }
    request.update(overrides)
    return request


# ---- configuration ----------------------------------------------------


def test_defaults_are_applied() -> None:
    config = resolve_config(env=KEY)

    assert config.api_base == DEFAULT_API_BASE
    assert config.host == DEFAULT_HOST
    assert config.port == DEFAULT_PORT
    assert config.model is None
    assert config.is_local_only


def test_missing_api_key_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="CARACAT_API_KEY"):
        resolve_config(env={})


def test_blank_api_key_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="CARACAT_API_KEY"):
        resolve_config(env={"CARACAT_API_KEY": "   "})


def test_arguments_win_over_environment() -> None:
    env = {**KEY, "CARACAT_MODEL": "from-env", "CARACAT_PORT": "9000"}

    config = resolve_config(env=env, model="from-arg", port=9100)

    assert config.model == "from-arg"
    assert config.port == 9100


def test_environment_is_used_when_no_argument_is_given() -> None:
    env = {**KEY, "CARACAT_MODEL": "from-env", "CARACAT_PORT": "9000"}

    config = resolve_config(env=env)

    assert config.model == "from-env"
    assert config.port == 9000


def test_trailing_slash_on_the_api_base_is_dropped() -> None:
    config = resolve_config(env=KEY, api_base="https://example.org/v1/")

    assert config.api_base == "https://example.org/v1"


def test_http_to_a_remote_host_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="only allowed for a local endpoint"):
        resolve_config(env=KEY, api_base="http://example.org/v1")


@pytest.mark.parametrize(
    "base",
    ["http://localhost:11434/v1", "http://127.0.0.1:8080/v1"],
)
def test_http_to_a_local_runtime_is_allowed(base: str) -> None:
    assert resolve_config(env=KEY, api_base=base).api_base == base


def test_a_url_without_a_scheme_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="must start with"):
        resolve_config(env=KEY, api_base="example.org/v1")


def test_an_unsupported_scheme_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="unsupported URL scheme"):
        resolve_config(env=KEY, api_base="ftp://example.org/v1")


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_a_port_out_of_range_is_refused(port: int) -> None:
    with pytest.raises(InterfaceConfigError, match="between 1 and 65535"):
        resolve_config(env=KEY, port=port)


def test_a_non_numeric_port_is_refused() -> None:
    with pytest.raises(InterfaceConfigError, match="must be a number"):
        resolve_config(env={**KEY, "CARACAT_PORT": "eight"})


def test_a_non_local_host_is_flagged() -> None:
    assert not resolve_config(env=KEY, host="0.0.0.0").is_local_only


def test_public_settings_never_expose_the_key() -> None:
    settings = resolve_config(env=KEY, model="some/model").public_settings()

    assert settings == {
        "api_base": DEFAULT_API_BASE,
        "default_model": "some/model",
        "has_api_key": True,
    }
    assert "test-key" not in repr(settings)


# ---- upstream routing -------------------------------------------------


@pytest.mark.parametrize("path", ["chat/completions", "models"])
def test_allowed_upstream_paths(path: str) -> None:
    assert (
        upstream_url("https://example.org/v1", path) == f"https://example.org/v1/{path}"
    )


@pytest.mark.parametrize(
    "path",
    ["", "admin", "../keys", "https://evil.example/steal", "chat/completions/../keys"],
)
def test_the_server_is_not_an_open_proxy(path: str) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        upstream_url("https://example.org/v1", path)


# ---- request validation -----------------------------------------------


def test_a_valid_request_becomes_a_payload() -> None:
    payload = build_chat_payload(chat_request())

    assert payload == {
        "model": "some/model",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
    }


def test_the_default_model_fills_in_when_none_is_chosen() -> None:
    payload = build_chat_payload(chat_request(model=""), default_model="fallback/model")

    assert payload["model"] == "fallback/model"


def test_a_request_without_any_model_is_refused() -> None:
    with pytest.raises(ChatRequestError, match="no model selected"):
        build_chat_payload(chat_request(model=None))


def test_the_body_must_be_an_object() -> None:
    with pytest.raises(ChatRequestError, match="must be a JSON object"):
        build_chat_payload(["not", "an", "object"])


@pytest.mark.parametrize("messages", [[], None, "hello", {}])
def test_messages_must_be_a_non_empty_list(messages: object) -> None:
    with pytest.raises(ChatRequestError, match="non-empty list"):
        build_chat_payload(chat_request(messages=messages))


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(ChatRequestError, match="allowed roles"):
        build_chat_payload(chat_request(messages=[{"role": "root", "content": "hi"}]))


def test_non_string_content_is_refused() -> None:
    with pytest.raises(ChatRequestError, match="string content"):
        build_chat_payload(chat_request(messages=[{"role": "user", "content": 42}]))


def test_too_many_messages_are_refused() -> None:
    flood = [{"role": "user", "content": "hi"}] * 201

    with pytest.raises(ChatRequestError, match="the limit is 200"):
        build_chat_payload(chat_request(messages=flood))


def test_oversized_content_is_refused() -> None:
    huge = [{"role": "user", "content": "x" * 100_001}]

    with pytest.raises(ChatRequestError, match="characters long"):
        build_chat_payload(chat_request(messages=huge))


def test_temperature_is_range_checked() -> None:
    assert build_chat_payload(chat_request(temperature=0.7))["temperature"] == 0.7

    with pytest.raises(ChatRequestError, match="between 0 and 2"):
        build_chat_payload(chat_request(temperature=5))


def test_a_boolean_is_not_a_temperature() -> None:
    with pytest.raises(ChatRequestError, match="must be a number"):
        build_chat_payload(chat_request(temperature=True))


def test_max_tokens_is_range_checked() -> None:
    assert build_chat_payload(chat_request(max_tokens=256))["max_tokens"] == 256

    with pytest.raises(ChatRequestError, match="between 1 and"):
        build_chat_payload(chat_request(max_tokens=0))


def test_unknown_fields_are_dropped_rather_than_forwarded() -> None:
    payload = build_chat_payload(chat_request(tools=[{"evil": True}], user="someone"))

    assert set(payload) == {"model", "messages", "stream"}


def test_streaming_can_be_switched_off() -> None:
    assert build_chat_payload(chat_request(), stream=False)["stream"] is False


# ---- redaction --------------------------------------------------------


def test_redact_removes_the_key() -> None:
    assert redact("failed for sk-secret-123", "sk-secret-123") == "failed for ***"


def test_redact_is_a_no_op_without_a_secret() -> None:
    assert redact("nothing to hide", "") == "nothing to hide"
