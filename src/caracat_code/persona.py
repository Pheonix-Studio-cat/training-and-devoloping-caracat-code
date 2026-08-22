"""Loading an assistant's personality from a file.

A personality lives in ``prompts/`` rather than in a string in the source, so
that changing how an assistant behaves is an edit to a text file and a page
reload -- not a code change.

There are two of them, and they are two different assistants rather than two
moods of one: ``code`` is Caracat Code on Qwen3-Coder-Next, ``chat`` is Caracat
AI on gpt-oss-20b. Each says in its own text which model it is based on, so the
assistant answers that question correctly without the interface having to tell
it.

The file may begin with a human-readable header explaining itself, separated
from the prompt by a line containing only ``---``. Everything after that line is
what the model receives. A file without such a separator is used in full.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "DEFAULT_PERSONA_PATH",
    "MAX_PERSONA_CHARS",
    "PERSONA_FILES",
    "PersonaError",
    "extract_prompt",
    "load_persona",
    "persona_path",
]

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

PERSONA_FILES = {
    "code": "caracat_persona.md",
    "chat": "caracat_ai_persona.md",
}
"""The assistants, by name. A name that is not here is not loadable at all.

Names rather than paths, because these are also what the interface sends. A
caller that could name any file would be a way to read any file.
"""

DEFAULT_PERSONA_PATH = PROMPTS_DIR / PERSONA_FILES["code"]

MAX_PERSONA_CHARS = 50_000
"""A system prompt larger than this is a mistake, not a personality."""

SEPARATOR = "---"


class PersonaError(ValueError):
    """Raised when the personality file is missing, empty or unusable."""


def extract_prompt(text: str) -> str:
    """Return the part of ``text`` that is sent to the model.

    Everything before the first line consisting only of ``---`` is treated as a
    header for human readers and dropped. Without such a line the whole text is
    the prompt.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == SEPARATOR:
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def persona_path(name: str) -> Path:
    """Return the file for the assistant called ``name``.

    Raises:
        PersonaError: If ``name`` is not one of :data:`PERSONA_FILES`.
    """
    try:
        filename = PERSONA_FILES[name]
    except KeyError:
        known = ", ".join(sorted(PERSONA_FILES))
        raise PersonaError(
            f"there is no assistant called {name!r}; there is {known}"
        ) from None
    return PROMPTS_DIR / filename


def load_persona(path: str | Path | None = None) -> str:
    """Read a personality file and return the system prompt it contains.

    Args:
        path: A name from :data:`PERSONA_FILES` (``"code"`` or ``"chat"``), or a
            path to a file of your own. Defaults to :data:`DEFAULT_PERSONA_PATH`.

            A bare name is resolved inside ``prompts/``; anything else is taken
            as a path, so ``--persona ~/mine.md`` keeps working.

    Raises:
        PersonaError: If the file is missing, unreadable, empty or oversized.
    """
    if path is None:
        source = DEFAULT_PERSONA_PATH
    elif isinstance(path, str) and path in PERSONA_FILES:
        source = persona_path(path)
    else:
        source = Path(path)

    if not source.is_file():
        raise PersonaError(
            f"personality file not found: {source}\n"
            "Pass --persona with a path to your own file, or --no-persona to "
            "start without one."
        )

    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PersonaError(f"could not read {source}: {exc}") from exc

    if len(text) > MAX_PERSONA_CHARS:
        raise PersonaError(
            f"{source} is {len(text)} characters, the limit is {MAX_PERSONA_CHARS}. "
            "A system prompt this long crowds out the conversation it is meant "
            "to shape."
        )

    prompt = extract_prompt(text)
    if not prompt:
        raise PersonaError(
            f"{source} contains no prompt. Everything after the first '---' line "
            "is sent to the model, and there is nothing there."
        )
    return prompt
