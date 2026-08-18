"""Tests for the front matter the Hugging Face Space is configured by.

`space/README.md` is not documentation with a header on top -- its front matter
*is* the Space's configuration, and the Hub validates it on upload. A mistake
here fails after the merge, in a workflow run, which is the slowest and least
obvious place to find out.

So the rules the Hub enforces are asserted here instead, where they fail in the
pull request. Each one below was learned from a real failed upload or from the
Space's own requirements, not invented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

README = Path(__file__).resolve().parent.parent / "space" / "README.md"

MAX_SHORT_DESCRIPTION = 60
"""The Hub's limit. Exceeding it fails the upload with:

    Invalid metadata in README.md.
    - "short_description" length must be less than or equal to 60 characters
"""


def front_matter() -> dict[str, str]:
    """The YAML block, read without a YAML parser.

    The values here are all plain scalars, and a test that needs a dependency to
    check a nine-line header would be the wrong trade.
    """
    text = README.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "the Space README must open with front matter"
    _, block, _ = text.split("---\n", 2)
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_the_short_description_fits_the_hub_limit() -> None:
    """The failure this test exists to prevent, stated as a length."""
    description = front_matter()["short_description"]

    assert len(description) <= MAX_SHORT_DESCRIPTION, (
        f"short_description is {len(description)} characters; the Hub rejects "
        f"anything over {MAX_SHORT_DESCRIPTION} and the upload fails after the merge"
    )


def test_the_space_is_declared_static() -> None:
    """A static Space is a decision, not a default.

    Only static Spaces are free, and the page is built to work without a server.
    An sdk of docker or gradio here would mean the Space and the page disagree
    about whether anything is running.
    """
    fields = front_matter()

    assert fields["sdk"] == "static"
    assert fields["app_file"] == "index.html"
    assert "app_port" not in fields, "app_port belongs to a Space that runs something"


@pytest.mark.parametrize("field", ["title", "emoji", "license", "short_description"])
def test_the_required_fields_are_present_and_filled(field: str) -> None:
    fields = front_matter()

    assert field in fields, f"the Space front matter is missing {field!r}"
    assert fields[field], f"{field!r} is empty"


def test_the_license_matches_the_project() -> None:
    assert front_matter()["license"] == "apache-2.0"


def test_the_readme_does_not_promise_a_server() -> None:
    """The Space has none, and saying otherwise would be the harmful mistake.

    On a static Space the API key is held in the visitor's browser. A README
    claiming it stays server-side would describe a protection that is not there.
    """
    body = README.read_text(encoding="utf-8").lower()

    assert "in your browser" in body

    # Only affirmative claims count. The README does say "there is no Space
    # secret to configure", and a test that tripped on that would be telling the
    # truth to shut up.
    for claim in (
        "key stays in the server",
        "key stays in this process",
        "never reaches this page",
        "the key stays in the space",
    ):
        assert claim not in body, f"the Space README must not claim {claim!r}"
