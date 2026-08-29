"""Nothing leaves this repository except what is named, one file at a time.

Two workflows upload to Hugging Face, and both mirror rather than merge: what
lands in the uploaded directory becomes public, and what is missing from it is
deleted on the Hub. So the question "what does this project publish?" has to be
answerable by reading the workflow, not by running it.

The rule is an allowlist:

* `sync-to-huggingface.yml` points the mirror at `hf/` and nothing else;
* `sync-to-space.yml` assembles a directory by copying files it names one by
  one, and refuses anything that is not `.html` or `.md`.

Both are one careless edit away from being an opt-out instead -- a `cp -r`, a
glob, a subdirectory of `.`. That edit would not fail anywhere: the upload would
succeed and simply carry more than intended, which for a public model repository
is the failure that cannot be taken back. Hence these tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
HF_SYNC = WORKFLOWS / "sync-to-huggingface.yml"
SPACE_SYNC = WORKFLOWS / "sync-to-space.yml"

ALLOWED_SUBDIRECTORIES = {"hf", "hf-ai", "hf-image", "space-build"}
"""The only directories a sync step may be pointed at.

``hf/``, ``hf-ai/`` and ``hf-image/`` are written by hand and hold exactly what
each model repository should show -- one per card, because putting two in one
directory would put one model's attribution on the other's card.
``space-build/`` is assembled during the run from named files.

Anything else -- ``.``, ``src``, a variable -- would publish the repository.
Adding an entry here is meant to be a decision someone makes on purpose.
"""


def sync_workflows() -> list[Path]:
    """Every workflow that mirrors anything to the Hub.

    Found rather than listed. The first version of this file named two
    workflows by hand, and when a third was added it sailed past every
    assertion below -- the file stayed green while covering less than it looked
    like it covered. A workflow that publishes is now caught by existing, not
    by being remembered.
    """
    found = [
        path
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if "hub-sync" in path.read_text(encoding="utf-8")
    ]
    assert found, "no publishing workflow found; this file would prove nothing"
    return found


def test_every_publishing_workflow_is_covered_here() -> None:
    # The guard on the guard. A new publishing workflow must be looked at, not
    # merely swept in by a glob that nobody rereads.
    assert {path.name for path in sync_workflows()} == {
        "sync-to-huggingface.yml",
        "sync-caracat-ai-to-huggingface.yml",
        "sync-caracat-image-to-huggingface.yml",
        "sync-to-space.yml",
    }


def test_the_model_repositories_stay_apart() -> None:
    """One directory per card, and none carries another's attribution.

    Both model repositories are public. A card naming the wrong base model
    would be this project's plainest rule broken in its most visible place.
    """
    root = WORKFLOWS.parent.parent

    # Whitespace is collapsed and blockquote markers dropped first: these are
    # claims about sentences, and a sentence that happens to wrap across two
    # lines of a quoted block is the same sentence.
    def flat(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        lines = [line.lstrip("> ").rstrip() for line in text.splitlines()]
        return " ".join(" ".join(lines).split())

    code_card = flat(root / "hf" / "README.md")
    ai_card = flat(root / "hf-ai" / "README.md")
    image_card = flat(root / "hf-image" / "README.md")

    assert "Qwen3-Coder-Next" in code_card
    assert "gpt-oss" not in code_card
    assert "Z-Image" not in code_card

    assert "based on gpt-oss-20b by OpenAI" in ai_card
    assert "Caracat AI is based on Qwen" not in ai_card

    assert "based on Z-Image-Turbo by Tongyi-MAI" in image_card
    # The image card names the other two only in its overview table, never as
    # the thing generating pictures.
    assert "Image generation in Caracat AI is based on Z-Image" in image_card

    # None claims weights it does not have.
    assert "no weights are published" in code_card.lower()
    assert "no weights in this repository" in ai_card.lower()
    assert "no weights in this repository" in image_card.lower()


def sync_steps(workflow: Path) -> list[dict]:
    """Every step that hands a directory to the mirroring action."""
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps = []
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            if "hub-sync" in str(step.get("uses", "")):
                steps.append(step)
    return steps


@pytest.mark.parametrize("workflow", sync_workflows(), ids=lambda p: p.name)
def test_the_mirror_is_pointed_at_an_allowed_directory(workflow: Path) -> None:
    steps = sync_steps(workflow)
    assert steps, f"{workflow.name} has no sync step; this test would prove nothing"

    for step in steps:
        target = step.get("with", {}).get("subdirectory")
        assert target in ALLOWED_SUBDIRECTORIES, (
            f"{workflow.name} mirrors {target!r}, which is not one of "
            f"{sorted(ALLOWED_SUBDIRECTORIES)} -- that would publish more than "
            "the files this project intends to make public"
        )


def test_the_space_directory_is_filled_by_naming_files_not_by_globbing() -> None:
    text = SPACE_SYNC.read_text(encoding="utf-8")

    copies = re.findall(r"^\s*cp\s+(.*)$", text, re.M)
    assert copies, "no cp lines found; this test would prove nothing"

    for line in copies:
        assert "-r" not in line.split(), (
            f"recursive copy into the published directory: {line.strip()!r}. "
            "A directory copy publishes whatever is in it later, including "
            "files nobody reviewed."
        )
        assert "*" not in line and "?" not in line, (
            f"glob in a copy into the published directory: {line.strip()!r}. "
            "What is published must be a decision, not a pattern match."
        )


@pytest.mark.parametrize("workflow", sync_workflows(), ids=lambda p: p.name)
def test_a_sync_only_wakes_for_the_directory_it_publishes(workflow: Path) -> None:
    """Each publishing workflow watches its own directory and no more.

    `on: push: paths:` is not a security control -- `workflow_dispatch` exists
    -- but a sync that runs on every push is a sync nobody watches, and one
    that watches a directory it does not publish is a sync nobody can reason
    about.

    The directory is read from the workflow's own sync step rather than named
    here, so a new workflow is held to this without anyone remembering to add
    it. Naming it was how the AI workflow slipped past on its first day.
    """
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    # `on` is parsed as the boolean True by YAML 1.1, which is why this is not
    # simply data["on"].
    triggers = data[True] if True in data else data["on"]
    paths = triggers["push"]["paths"]

    published = {step["with"]["subdirectory"] for step in sync_steps(workflow)}
    assert len(published) == 1, f"{workflow.name} publishes {published}"
    directory = next(iter(published))

    # space-build/ does not exist in the repository -- it is assembled during
    # the run -- so that workflow watches the sources it is assembled from.
    watched_for = "space" if directory == "space-build" else directory

    assert any(p.startswith(watched_for + "/") for p in paths), (
        f"{workflow.name} publishes {published} but its push paths are {paths}"
    )
    assert not any(p in {"**", "*", "."} for p in paths), (
        f"{workflow.name} is triggered by {paths}, which is every push"
    )


def test_the_space_upload_still_refuses_anything_but_html_and_markdown() -> None:
    text = SPACE_SYNC.read_text(encoding="utf-8")

    # The guard step, not merely a comment about one.
    assert "! -name '*.html' ! -name '*.md'" in text, (
        "the step that refuses non-static files is gone; a static Space runs "
        "nothing, so anything else there is dead weight at best"
    )
