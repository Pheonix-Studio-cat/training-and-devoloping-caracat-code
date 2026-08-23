"""What the Space publishes must be what the page asks for.

The static Space has no server: the page fetches its personality files by name,
straight off the Space's own file listing. The workflow that publishes the
Space names every file it uploads one by one, deliberately -- so that what lands
on a public page is a decision rather than the result of a glob.

Those two lists have to agree, and nothing makes them agree automatically. A
file the page fetches but the workflow does not copy produces no error anywhere:
the upload succeeds, the page loads, and one personality is silently missing.
That is the failure this file exists to catch, in the pull request rather than
in a Space nobody reloads for a week.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "interface" / "index.html"
WORKFLOW = ROOT / ".github" / "workflows" / "sync-to-space.yml"
PROMPTS = ROOT / "prompts"


def published_files() -> set[str]:
    """The basenames the workflow copies into the directory it uploads."""
    text = WORKFLOW.read_text()
    copies = re.findall(r"^\s*cp\s+\S+\s+space-build/(\S+)\s*$", text, re.M)
    return set(copies)


def fetched_markdown() -> set[str]:
    """The .md files the page names, and therefore expects the Space to hold.

    Every filename literal, not only the ones inside a ``fetch(...)`` call. The
    page loads them through a lookup table, so matching on ``fetch("...")``
    found nothing at all and the assertions below passed while proving nothing
    -- which is a worse state than failing.
    """
    literals = set(re.findall(r'"([A-Za-z0-9_.-]+\.md)"', PAGE.read_text()))
    # A bare extension (".md") is a suffix check somewhere, not a filename.
    return {name for name in literals if name != ".md"}


def test_every_markdown_file_the_page_fetches_is_published() -> None:
    missing = fetched_markdown() - published_files()

    assert not missing, (
        f"the page fetches {sorted(missing)}, which the Space workflow does not "
        "upload; on the Space those personalities would silently be empty"
    )


def test_every_personality_the_page_fetches_actually_exists() -> None:
    # The workflow's `cp` would fail loudly on a missing file, but only after a
    # merge. This fails in the pull request instead.
    for name in fetched_markdown():
        assert (PROMPTS / name).is_file(), (
            f"prompts/{name} is named by the page but does not exist"
        )


def test_both_personalities_reach_the_space() -> None:
    published = published_files()

    assert "caracat_persona.md" in published
    assert "caracat_ai_persona.md" in published


def test_the_space_still_receives_only_static_files() -> None:
    # The Space runs nothing; anything but .html and .md would be dead weight
    # that looks like it does something.
    for name in published_files():
        assert name.endswith((".html", ".md")), (
            f"{name} does not belong on a static Space"
        )
