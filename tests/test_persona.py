"""Tests for loading the assistant's personality."""

from __future__ import annotations

from pathlib import Path

import pytest

from caracat_code.persona import (
    DEFAULT_PERSONA_PATH,
    MAX_PERSONA_CHARS,
    PersonaError,
    extract_prompt,
    load_persona,
)


def test_the_header_before_the_separator_is_dropped() -> None:
    text = "explanation for humans\n\n---\n\nYou are Caracat Code."

    assert extract_prompt(text) == "You are Caracat Code."


def test_a_file_without_a_separator_is_used_whole() -> None:
    assert extract_prompt("You are Caracat Code.") == "You are Caracat Code."


def test_only_the_first_separator_splits() -> None:
    text = "header\n---\nprompt line\n---\nstill the prompt"

    assert extract_prompt(text) == "prompt line\n---\nstill the prompt"


def test_loading_a_file(tmp_path: Path) -> None:
    path = tmp_path / "persona.md"
    path.write_text("notes\n---\nBe useful.", encoding="utf-8")

    assert load_persona(path) == "Be useful."


def test_a_missing_file_is_reported_with_a_way_out(tmp_path: Path) -> None:
    with pytest.raises(PersonaError, match="--no-persona"):
        load_persona(tmp_path / "nope.md")


def test_a_file_with_no_prompt_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "persona.md"
    path.write_text("only a header\n---\n   \n", encoding="utf-8")

    with pytest.raises(PersonaError, match="contains no prompt"):
        load_persona(path)


def test_an_oversized_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "persona.md"
    path.write_text("x" * (MAX_PERSONA_CHARS + 1), encoding="utf-8")

    with pytest.raises(PersonaError, match="crowds out"):
        load_persona(path)


# ---- the shipped personality ------------------------------------------


def test_the_shipped_personality_loads() -> None:
    prompt = load_persona()

    assert prompt.startswith("You are Caracat Code")
    assert len(prompt) < MAX_PERSONA_CHARS


def test_the_shipped_file_is_where_the_default_points() -> None:
    assert DEFAULT_PERSONA_PATH.is_file()
    assert DEFAULT_PERSONA_PATH.name == "caracat_persona.md"


def test_the_personality_carries_the_rules_it_is_for() -> None:
    prompt = load_persona().lower()

    # The project owner's rule: ask rather than guess, and do not be timid.
    assert "ask" in prompt
    assert "guess" in prompt
    assert "timid" in prompt
    # Language behaviour, including the identifiers exception.
    assert "language the person wrote" in prompt
    assert "identifiers in code stay english" in prompt
    # Scope, and the honest attribution.
    assert "programming only" in prompt
    assert "qwen3-coder-next" in prompt


def test_the_personality_forbids_empty_praise() -> None:
    prompt = load_persona().lower()

    assert "great question" in prompt  # named as something not to do
    assert "correctness beats agreeableness" in prompt


def test_the_header_is_not_sent_to_the_model() -> None:
    raw = DEFAULT_PERSONA_PATH.read_text(encoding="utf-8")

    assert "loaded by the local interface" in raw
    assert "loaded by the local interface" not in load_persona()
