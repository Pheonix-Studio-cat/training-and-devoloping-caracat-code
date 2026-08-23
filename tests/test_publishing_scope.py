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

ALLOWED_SUBDIRECTORIES = {"hf", "space-build"}
"""The only two directories a sync step may be pointed at.

``hf/`` is written by hand and holds exactly what the model repository should
show. ``space-build/`` is assembled during the run from named files. Anything
else -- ``.``, ``src``, a variable -- would publish the repository.
"""


def sync_steps(workflow: Path) -> list[dict]:
    """Every step that hands a directory to the mirroring action."""
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps = []
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            if "hub-sync" in str(step.get("uses", "")):
                steps.append(step)
    return steps


@pytest.mark.parametrize("workflow", [HF_SYNC, SPACE_SYNC], ids=lambda p: p.name)
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


def test_the_model_repository_sync_only_wakes_for_its_own_directory() -> None:
    # `on: push: paths:` is not a security control -- workflow_dispatch exists
    # -- but a sync that runs on every push is a sync nobody watches.
    data = yaml.safe_load(HF_SYNC.read_text(encoding="utf-8"))
    # `on` is parsed as the boolean True by YAML 1.1, which is why this is not
    # simply data["on"].
    triggers = data[True] if True in data else data["on"]
    paths = triggers["push"]["paths"]

    assert any(p.startswith("hf/") for p in paths)
    assert not any(p in {"**", "*", "."} for p in paths), (
        f"the model repository sync is triggered by {paths}, which is every push"
    )


def test_the_space_upload_still_refuses_anything_but_html_and_markdown() -> None:
    text = SPACE_SYNC.read_text(encoding="utf-8")

    # The guard step, not merely a comment about one.
    assert "! -name '*.html' ! -name '*.md'" in text, (
        "the step that refuses non-static files is gone; a static Space runs "
        "nothing, so anything else there is dead weight at best"
    )
