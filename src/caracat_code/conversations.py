"""Keeping conversations, so closing a tab does not throw the work away.

Stored as one JSON file per conversation, **outside the repository** by default.
That is deliberate: conversations contain whatever you pasted into them, and a
default that writes into a git checkout is a default that eventually commits
somebody's code to a public repository.

Filenames come from a generated identifier, never from the title. A title is
user text, and user text that reaches a filesystem path is a directory
traversal waiting to happen.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from caracat_code.interface import ALLOWED_ROLES

__all__ = [
    "MAX_CONVERSATIONS",
    "Conversation",
    "ConversationError",
    "ConversationStore",
    "default_store_path",
]

IDENTIFIER = re.compile(r"^[0-9a-f]{12}$")
MAX_TITLE_CHARS = 200
MAX_MESSAGES = 500
MAX_CONTENT_CHARS = 100_000
MAX_CONVERSATIONS = 500


class ConversationError(ValueError):
    """Raised when a conversation cannot be stored, found or read."""


def default_store_path() -> Path:
    """Where conversations live when nothing else is configured.

    Follows XDG on Linux, and stays out of the repository either way.
    """
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "caracat-code" / "conversations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Conversation:
    """One saved conversation."""

    title: str
    messages: tuple[Mapping[str, str], ...]
    model: str | None = None
    identifier: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def summary(self) -> dict[str, object]:
        """Enough to list it without loading every message."""
        return {
            "id": self.identifier,
            "title": self.title,
            "model": self.model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.summary(),
            "messages": [dict(message) for message in self.messages],
        }


def _validate_identifier(identifier: object) -> str:
    """Only a generated identifier may become part of a path."""
    if not isinstance(identifier, str) or not IDENTIFIER.match(identifier):
        raise ConversationError(
            f"{identifier!r} is not a conversation id. Ids are generated, and "
            "nothing else is accepted -- a name taken from user text is how a "
            "path escapes its directory."
        )
    return identifier


def _validate_messages(raw: object) -> tuple[Mapping[str, str], ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConversationError("'messages' must be a list")
    if len(raw) > MAX_MESSAGES:
        raise ConversationError(
            f"a conversation may hold {MAX_MESSAGES} messages, got {len(raw)}"
        )

    messages: list[Mapping[str, str]] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise ConversationError(f"message {index} must be an object")
        role = entry.get("role")
        if role not in ALLOWED_ROLES:
            raise ConversationError(f"message {index} has an unknown role {role!r}")
        content = entry.get("content")
        if not isinstance(content, str):
            raise ConversationError(f"message {index} must have string content")
        if len(content) > MAX_CONTENT_CHARS:
            raise ConversationError(
                f"message {index} is longer than {MAX_CONTENT_CHARS} characters"
            )
        messages.append({"role": role, "content": content})
    return tuple(messages)


def _validate_title(raw: object) -> str:
    title = raw if isinstance(raw, str) else ""
    title = " ".join(title.split()).strip()
    if not title:
        return "Untitled conversation"
    return title[:MAX_TITLE_CHARS]


@dataclass(frozen=True)
class ConversationStore:
    """A directory of saved conversations."""

    root: Path

    @classmethod
    def open(cls, path: str | Path | None = None) -> ConversationStore:
        root = Path(path).expanduser() if path is not None else default_store_path()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConversationError(
                f"could not create the conversation directory {root}: {exc}"
            ) from exc
        return cls(root=root.resolve())

    def _path(self, identifier: str) -> Path:
        return self.root / f"{_validate_identifier(identifier)}.json"

    def save(self, raw: object) -> Conversation:
        """Store a conversation sent by the browser, and return what was stored.

        An ``id`` in the payload updates that conversation; without one a new
        conversation is created.

        Raises:
            ConversationError: If the payload is unusable or the store is full.
        """
        if not isinstance(raw, Mapping):
            raise ConversationError("a conversation must be an object")

        messages = _validate_messages(raw.get("messages"))
        if not messages:
            raise ConversationError("there is nothing to save: no messages")

        identifier = raw.get("id")
        if identifier is None:
            if len(self.list()) >= MAX_CONVERSATIONS:
                raise ConversationError(
                    f"the store already holds {MAX_CONVERSATIONS} conversations. "
                    "Delete some before saving another."
                )
            conversation = Conversation(
                title=_validate_title(raw.get("title")),
                messages=messages,
                model=raw.get("model") if isinstance(raw.get("model"), str) else None,
            )
        else:
            existing = self.load(_validate_identifier(identifier))
            conversation = Conversation(
                title=_validate_title(raw.get("title") or existing.title),
                messages=messages,
                model=raw.get("model") if isinstance(raw.get("model"), str) else None,
                identifier=existing.identifier,
                created_at=existing.created_at,
                updated_at=_now(),
            )

        path = self._path(conversation.identifier)
        try:
            path.write_text(
                json.dumps(conversation.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConversationError(f"could not save the conversation: {exc}") from exc
        return conversation

    def load(self, identifier: str) -> Conversation:
        """Read one conversation.

        Raises:
            ConversationError: If the id is invalid, unknown or unreadable.
        """
        path = self._path(identifier)
        if not path.is_file():
            raise ConversationError(f"no conversation with id {identifier!r}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConversationError(f"{path.name} could not be read: {exc}") from exc
        if not isinstance(raw, Mapping):
            raise ConversationError(f"{path.name} does not hold a conversation")

        return Conversation(
            title=_validate_title(raw.get("title")),
            messages=_validate_messages(raw.get("messages")),
            model=raw.get("model") if isinstance(raw.get("model"), str) else None,
            identifier=_validate_identifier(raw.get("id")),
            created_at=str(raw.get("created_at") or _now()),
            updated_at=str(raw.get("updated_at") or _now()),
        )

    def list(self) -> list[dict[str, object]]:
        """Every stored conversation, newest first. Unreadable files are skipped."""
        summaries: list[dict[str, object]] = []
        for path in self.root.glob("*.json"):
            if not IDENTIFIER.match(path.stem):
                continue
            try:
                summaries.append(self.load(path.stem).summary())
            except ConversationError:
                continue  # a damaged file should not hide the healthy ones
        summaries.sort(key=lambda item: str(item["updated_at"]), reverse=True)
        return summaries

    def delete(self, identifier: str) -> None:
        """Remove one conversation.

        Raises:
            ConversationError: If the id is invalid or unknown.
        """
        path = self._path(identifier)
        if not path.is_file():
            raise ConversationError(f"no conversation with id {identifier!r}")
        try:
            path.unlink()
        except OSError as exc:
            raise ConversationError(f"could not delete {path.name}: {exc}") from exc
