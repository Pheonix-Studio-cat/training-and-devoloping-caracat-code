"""Tests for loading the assistant's personality."""

from __future__ import annotations

from pathlib import Path

import pytest

from caracat_code.persona import (
    DEFAULT_PERSONA_PATH,
    MAX_PERSONA_CHARS,
    PERSONA_FILES,
    PersonaError,
    extract_prompt,
    load_persona,
    persona_path,
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


# --- the other assistants --------------------------------------------------
#
# Three assistants on three base models. None is another with a different name,
# and the tests below guard the two things that would be wrong rather than
# merely different -- a wrong attribution, and identities bleeding into each
# other.


def test_every_assistant_is_loadable_by_name() -> None:
    assert sorted(PERSONA_FILES) == ["chat", "code", "pro"]
    assert load_persona("code") == load_persona()
    assert load_persona("chat")
    assert load_persona("pro")


def test_an_unknown_assistant_is_refused_rather_than_looked_up() -> None:
    # A name that reached a filesystem lookup would be a way to read any file.
    with pytest.raises(PersonaError) as excinfo:
        persona_path("../../etc/passwd")

    assert "no assistant called" in str(excinfo.value)


def test_caracat_ai_says_which_model_it_is_based_on() -> None:
    prompt = load_persona("chat").lower()

    assert "caracat ai" in prompt
    assert "gpt-oss-20b" in prompt
    assert "openai" in prompt
    # It must not claim to be trained from scratch.
    assert "not trained from scratch" in prompt


def test_caracat_pro_says_which_model_it_is_based_on() -> None:
    prompt = load_persona("pro").lower()

    assert "caracat pro" in prompt
    assert "deepseek-v3.1" in prompt
    assert "deepseek" in prompt
    assert "not trained from scratch" in prompt


def test_the_assistants_do_not_claim_to_be_each_other() -> None:
    # Emphasis is stripped: the sentence matters, not whether a word is bold.
    chat = load_persona("chat").lower().replace("*", "")
    code = load_persona("code").lower().replace("*", "")
    pro = load_persona("pro").lower().replace("*", "")

    # Each knows the others exist and knows it is not them.
    assert "you are not caracat code" in chat
    assert "you are not caracat ai and not caracat code" in pro

    # None borrows another's base model. Naming a sibling's model *after*
    # saying "I am not that one" is the point of the sentence, so only the text
    # before the disclaimer is checked.
    assert "qwen3-coder-next" not in chat.split("caracat code")[0]
    assert "gpt-oss" not in code
    assert "deepseek" not in chat
    assert "deepseek" not in code

    before_disclaimer = pro.split("you are not caracat ai")[0]
    assert "gpt-oss" not in before_disclaimer
    assert "qwen3" not in before_disclaimer


def test_caracat_pro_sends_small_jobs_to_the_cheaper_assistant() -> None:
    """The largest model saying so is a feature, not modesty.

    Caracat Pro runs on hundreds of billions of parameters and on the
    visitor's own key. A personality that never mentioned that would quietly
    spend someone else's money on questions the 20B model answers just as
    well.
    """
    pro = load_persona("pro").lower()

    assert "caracat ai" in pro
    assert "own hugging face key" in pro
    # Not merely the word "cost" -- that appears in "a confident wrong answer
    # costs more". The sentence that names the cheaper sibling is the point.
    assert "fraction of the cost" in pro


def test_the_general_assistants_know_they_cannot_draw() -> None:
    # The button is in front of the person; an assistant denying the feature
    # exists would contradict what they can see.
    for name in ("chat", "pro"):
        prompt = load_persona(name).lower()
        assert "z-image-turbo" in prompt, name
        assert "cannot make" in prompt or "you cannot" in prompt, name


def test_the_general_assistants_are_general_where_caracat_code_is_narrow() -> None:
    chat = load_persona("chat").lower()
    code = load_persona("code").lower()
    pro = load_persona("pro").lower()

    assert "programming only" in code
    assert "programming only" not in chat
    assert "programming only" not in pro
    assert "general assistant" in chat
    assert "general assistant" in pro
    # And it is honest about the two places being general gets dangerous.
    assert "professional" in chat
    assert "cannot look anything up" in chat
