"""Loading the assistant's personality from a file.

The personality lives in ``prompts/caracat_persona.md`` rather than in a string
in the source, so that changing how the assistant behaves is an edit to a text
file and a page reload -- not a code change.

The file may begin with a human-readable header explaining itself, separated
from the prompt by a line containing only ``---``. Everything after that line is
what the model receives. A file without such a separator is used in full.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "DEFAULT_PERSONA_PATH",
    "MAX_PERSONA_CHARS",
    "PersonaError",
    "extract_prompt",
    "load_persona",
]

DEFAULT_PERSONA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "caracat_persona.md"
)

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


def load_persona(path: str | Path | None = None) -> str:
    """Read the personality file and return the system prompt it contains.

    Args:
        path: File to read. Defaults to :data:`DEFAULT_PERSONA_PATH`.

    Raises:
        PersonaError: If the file is missing, unreadable, empty or oversized.
    """
    source = Path(path) if path is not None else DEFAULT_PERSONA_PATH

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
