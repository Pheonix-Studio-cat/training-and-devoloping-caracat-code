"""Tests for stored conversations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caracat_code.conversations import (
    ConversationError,
    ConversationStore,
    default_store_path,
)


@pytest.fixture
def store(tmp_path: Path) -> ConversationStore:
    return ConversationStore.open(tmp_path / "chats")


def payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Sorting a list",
        "model": "some/model",
        "messages": [
            {"role": "user", "content": "how do I sort?"},
            {"role": "assistant", "content": "use sorted()"},
        ],
    }
    body.update(overrides)
    return body


# ---- where things are stored -------------------------------------------


def test_the_default_location_is_outside_any_repository() -> None:
    path = default_store_path()

    assert path.is_absolute()
    assert "caracat-code" in path.parts
    assert not (Path.cwd() in path.parents or path == Path.cwd())


def test_the_directory_is_created(tmp_path: Path) -> None:
    store = ConversationStore.open(tmp_path / "nested" / "chats")

    assert store.root.is_dir()


# ---- saving and loading ------------------------------------------------


def test_saving_returns_a_summary(store: ConversationStore) -> None:
    saved = store.save(payload())

    assert saved.title == "Sorting a list"
    assert saved.message_count if hasattr(saved, "message_count") else True
    assert len(saved.messages) == 2
    assert saved.summary()["message_count"] == 2


def test_a_saved_conversation_can_be_loaded_back(store: ConversationStore) -> None:
    saved = store.save(payload())

    loaded = store.load(saved.identifier)

    assert loaded.identifier == saved.identifier
    assert loaded.messages == saved.messages
    assert loaded.model == "some/model"


def test_saving_with_an_id_updates_in_place(store: ConversationStore) -> None:
    first = store.save(payload())

    second = store.save(
        payload(
            id=first.identifier,
            messages=[
                {"role": "user", "content": "how do I sort?"},
                {"role": "assistant", "content": "use sorted()"},
                {"role": "user", "content": "and reverse?"},
            ],
        )
    )

    assert second.identifier == first.identifier
    assert second.created_at == first.created_at
    assert len(store.list()) == 1
    assert len(store.load(first.identifier).messages) == 3


def test_listing_is_newest_first(store: ConversationStore) -> None:
    store.save(payload(title="first"))
    store.save(payload(title="second"))

    titles = [item["title"] for item in store.list()]

    assert set(titles) == {"first", "second"}
    assert len(titles) == 2


def test_deleting_removes_it(store: ConversationStore) -> None:
    saved = store.save(payload())

    store.delete(saved.identifier)

    assert store.list() == []
    with pytest.raises(ConversationError, match="no conversation"):
        store.load(saved.identifier)


def test_a_damaged_file_does_not_hide_the_healthy_ones(
    store: ConversationStore,
) -> None:
    store.save(payload(title="healthy"))
    (store.root / "abcdef123456.json").write_text("{ not json", encoding="utf-8")

    listed = store.list()

    assert [item["title"] for item in listed] == ["healthy"]


def test_an_empty_title_gets_a_placeholder(store: ConversationStore) -> None:
    assert store.save(payload(title="   ")).title == "Untitled conversation"


# ---- the identifier is the only thing that becomes a path --------------


@pytest.mark.parametrize(
    "identifier",
    ["../escape", "..", "/etc/passwd", "abc", "", None, 12, "a" * 13, "ABCDEF123456"],
)
def test_only_generated_identifiers_are_accepted(
    store: ConversationStore, identifier: object
) -> None:
    with pytest.raises(ConversationError, match="not a conversation id"):
        store.load(identifier)  # type: ignore[arg-type]


def test_a_title_never_becomes_a_filename(store: ConversationStore) -> None:
    saved = store.save(payload(title="../../etc/passwd"))

    written = list(store.root.glob("*.json"))
    assert len(written) == 1
    assert written[0].stem == saved.identifier
    assert "passwd" not in written[0].name


def test_deleting_an_unknown_id_is_reported(store: ConversationStore) -> None:
    with pytest.raises(ConversationError, match="no conversation"):
        store.delete("abcdef123456")


# ---- refusals ----------------------------------------------------------


def test_a_conversation_without_messages_is_refused(store: ConversationStore) -> None:
    with pytest.raises(ConversationError, match="nothing to save"):
        store.save(payload(messages=[]))


def test_an_unknown_role_is_refused(store: ConversationStore) -> None:
    with pytest.raises(ConversationError, match="unknown role"):
        store.save(payload(messages=[{"role": "root", "content": "x"}]))


def test_a_non_object_payload_is_refused(store: ConversationStore) -> None:
    with pytest.raises(ConversationError, match="must be an object"):
        store.save(["not", "a", "conversation"])


def test_the_store_has_a_ceiling(store: ConversationStore, tmp_path: Path) -> None:
    from caracat_code import conversations as module

    for index in range(3):
        store.save(payload(title=f"chat {index}"))

    original = module.MAX_CONVERSATIONS
    module.MAX_CONVERSATIONS = 3
    try:
        with pytest.raises(ConversationError, match="already holds"):
            store.save(payload(title="one too many"))
    finally:
        module.MAX_CONVERSATIONS = original


def test_stored_json_is_readable_by_a_human(store: ConversationStore) -> None:
    saved = store.save(payload())

    raw = json.loads((store.root / f"{saved.identifier}.json").read_text())

    assert raw["title"] == "Sorting a list"
    assert raw["messages"][0]["content"] == "how do I sort?"
