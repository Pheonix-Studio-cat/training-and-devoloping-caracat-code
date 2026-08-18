"""Logic behind the local chat interface.

The interface is a small local web page that talks to an OpenAI-compatible
chat-completions endpoint. That protocol is the common denominator between
hosted providers and local runtimes, so one implementation covers all of them.

This module holds everything that can be tested without a network: reading the
configuration, restricting which upstream paths may be reached, and validating
what the browser sends before it is forwarded.

The API key is read from the environment and never leaves the server process:
the browser never sees it, and it is never written to a log or a response.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "ALLOWED_ROLES",
    "ALLOWED_UPSTREAM_PATHS",
    "DEFAULT_API_BASE",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "LOCAL_HOSTS",
    "ChatRequestError",
    "InterfaceConfig",
    "InterfaceConfigError",
    "build_chat_payload",
    "redact",
    "resolve_config",
    "upstream_url",
]

DEFAULT_API_BASE = "https://router.huggingface.co/v1"
"""Hugging Face's OpenAI-compatible router.

The default is Hugging Face because that is where this project lives and
where the base model is published. Any OpenAI-compatible endpoint works --
``--api-base`` takes another provider, or a local runtime.
"""
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

ALLOWED_ROLES = frozenset({"system", "user", "assistant"})
ALLOWED_UPSTREAM_PATHS = frozenset({"chat/completions", "models"})
"""The only upstream paths the server will reach. It is not an open proxy."""

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})

MAX_MESSAGES = 200
MAX_CONTENT_CHARS = 100_000
MAX_TEMPERATURE = 2.0
MAX_OUTPUT_TOKENS = 128_000


class InterfaceConfigError(ValueError):
    """Raised when the interface is not configured well enough to start."""


class ChatRequestError(ValueError):
    """Raised when the browser sends a request that will not be forwarded."""


@dataclass(frozen=True)
class InterfaceConfig:
    """Everything the local server needs in order to run."""

    api_base: str
    api_key: str
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    model: str | None = None

    @property
    def is_local_only(self) -> bool:
        """Whether the server is reachable only from this machine."""
        return self.host in LOCAL_HOSTS

    def public_settings(self) -> dict[str, object]:
        """Configuration safe to hand to the browser. Never includes the key."""
        return {
            "api_base": self.api_base,
            "default_model": self.model,
            "has_api_key": bool(self.api_key),
        }


def _normalize_api_base(value: str) -> str:
    base = value.strip().rstrip("/")
    if not base:
        raise InterfaceConfigError("the API base URL is empty")

    scheme, separator, remainder = base.partition("://")
    if not separator:
        raise InterfaceConfigError(
            f"the API base URL must start with https:// or http://, got {value!r}"
        )

    scheme = scheme.lower()
    if scheme == "https":
        return base
    if scheme == "http":
        host = remainder.split("/", 1)[0].rsplit(":", 1)[0]
        if host.lower() in LOCAL_HOSTS:
            return base
        raise InterfaceConfigError(
            f"plain http is only allowed for a local endpoint, got {value!r}. "
            "Sending an API key over http to a remote host would expose it."
        )
    raise InterfaceConfigError(f"unsupported URL scheme {scheme!r} in {value!r}")


def resolve_config(
    *,
    env: Mapping[str, str] | None = None,
    api_base: str | None = None,
    model: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> InterfaceConfig:
    """Build the interface configuration from arguments and the environment.

    Explicit arguments win over environment variables, which win over the
    defaults. The API key is only ever read from ``CARACAT_API_KEY`` -- there is
    deliberately no command-line flag for it, because that would put the key
    into the shell history and the process list.

    Raises:
        InterfaceConfigError: If the key is missing or a value is unusable.
    """
    environment = os.environ if env is None else env

    api_key = (environment.get("CARACAT_API_KEY") or "").strip()
    if not api_key:
        raise InterfaceConfigError(
            "CARACAT_API_KEY is not set. Export your provider's API key, for "
            "example:\n\n    export CARACAT_API_KEY='...'\n\n"
            "The key is read from the environment only. Never put it in a file "
            "inside this repository."
        )

    resolved_base = _normalize_api_base(
        api_base or environment.get("CARACAT_API_BASE") or DEFAULT_API_BASE
    )

    resolved_model = (model or environment.get("CARACAT_MODEL") or "").strip() or None

    resolved_host = (host or environment.get("CARACAT_HOST") or DEFAULT_HOST).strip()
    if not resolved_host:
        raise InterfaceConfigError("the host to bind to is empty")

    raw_port = port if port is not None else environment.get("CARACAT_PORT")
    try:
        resolved_port = int(raw_port) if raw_port is not None else DEFAULT_PORT
    except (TypeError, ValueError) as exc:
        raise InterfaceConfigError(f"port must be a number, got {raw_port!r}") from exc
    if not 1 <= resolved_port <= 65535:
        raise InterfaceConfigError(
            f"port must be between 1 and 65535, got {resolved_port}"
        )

    return InterfaceConfig(
        api_base=resolved_base,
        api_key=api_key,
        host=resolved_host,
        port=resolved_port,
        model=resolved_model,
    )


def upstream_url(api_base: str, path: str) -> str:
    """Build the URL for an allowed upstream path.

    Only the paths in :data:`ALLOWED_UPSTREAM_PATHS` can be reached, so a
    crafted request from the browser cannot turn the local server into a proxy
    for arbitrary destinations.

    Raises:
        ValueError: If ``path`` is not one of the allowed paths.
    """
    if path not in ALLOWED_UPSTREAM_PATHS:
        raise ValueError(f"upstream path {path!r} is not allowed")
    return f"{api_base.rstrip('/')}/{path}"


def _validate_messages(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not raw:
        raise ChatRequestError("'messages' must be a non-empty list")
    if len(raw) > MAX_MESSAGES:
        raise ChatRequestError(
            f"'messages' holds {len(raw)} entries, the limit is {MAX_MESSAGES}"
        )

    messages: list[dict[str, str]] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise ChatRequestError(f"message {index} must be an object")

        role = entry.get("role")
        if role not in ALLOWED_ROLES:
            raise ChatRequestError(
                f"message {index} has role {role!r}; allowed roles are "
                f"{', '.join(sorted(ALLOWED_ROLES))}"
            )

        content = entry.get("content")
        if not isinstance(content, str):
            raise ChatRequestError(f"message {index} must have string content")
        if len(content) > MAX_CONTENT_CHARS:
            raise ChatRequestError(
                f"message {index} is {len(content)} characters long, the limit "
                f"is {MAX_CONTENT_CHARS}"
            )

        messages.append({"role": role, "content": content})

    return messages


def build_chat_payload(
    raw: object, *, default_model: str | None = None, stream: bool = True
) -> dict[str, object]:
    """Turn a request from the browser into a payload for the upstream API.

    Every field is checked here rather than passed through, so the local server
    never forwards something it has not understood.

    Raises:
        ChatRequestError: If the request is unusable.
    """
    if not isinstance(raw, Mapping):
        raise ChatRequestError("the request body must be a JSON object")

    model = raw.get("model")
    if model is None or (isinstance(model, str) and not model.strip()):
        model = default_model
    if not isinstance(model, str) or not model.strip():
        raise ChatRequestError(
            "no model selected. Choose one in the interface, or start the "
            "server with --model."
        )

    payload: dict[str, object] = {
        "model": model.strip(),
        "messages": _validate_messages(raw.get("messages")),
        "stream": stream,
    }

    temperature = raw.get("temperature")
    if temperature is not None:
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise ChatRequestError(
                f"'temperature' must be a number, got {temperature!r}"
            )
        if not 0.0 <= float(temperature) <= MAX_TEMPERATURE:
            raise ChatRequestError(
                f"'temperature' must be between 0 and {MAX_TEMPERATURE}, "
                f"got {temperature}"
            )
        payload["temperature"] = float(temperature)

    max_tokens = raw.get("max_tokens")
    if max_tokens is not None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
            raise ChatRequestError(
                f"'max_tokens' must be an integer, got {max_tokens!r}"
            )
        if not 1 <= max_tokens <= MAX_OUTPUT_TOKENS:
            raise ChatRequestError(
                f"'max_tokens' must be between 1 and {MAX_OUTPUT_TOKENS}, "
                f"got {max_tokens}"
            )
        payload["max_tokens"] = max_tokens

    return payload


def redact(text: str, secret: str) -> str:
    """Replace ``secret`` wherever it appears in ``text``.

    Used on anything derived from an upstream error before it is shown or
    logged, so a key echoed back by a provider cannot leak onwards.
    """
    if not secret:
        return text
    return text.replace(secret, "***")
