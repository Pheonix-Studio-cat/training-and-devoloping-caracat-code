"""Tests for project file access.

The escape attempts matter most here: everything else is convenience, but a path
that leaves the project root is a way to read anything the user can read.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from caracat_code.workspace import (
    MAX_FILE_BYTES,
    Workspace,
    WorkspaceError,
    WorkspaceSecretError,
)

FAKE_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "node_modules" / "left-pad").mkdir(parents=True)

    (root / "README.md").write_text("# Project\n", encoding="utf-8")
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (root / "node_modules" / "left-pad" / "index.js").write_text("x", encoding="utf-8")
    (root / ".env").write_text(f"API_KEY={FAKE_KEY}\n", encoding="utf-8")
    (root / "server.key").write_text("private\n", encoding="utf-8")

    (tmp_path / "outside.txt").write_text("not yours\n", encoding="utf-8")
    return root


@pytest.fixture
def workspace(project: Path) -> Workspace:
    return Workspace.open(project)


# ---- escaping the root -------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "./../../outside.txt",
        "src/../../../etc/passwd",
    ],
)
def test_climbing_out_of_the_project_is_refused(
    workspace: Workspace, path: str
) -> None:
    with pytest.raises(WorkspaceError, match="outside the project"):
        workspace.read(path)


def test_an_absolute_path_is_refused(workspace: Workspace) -> None:
    with pytest.raises(WorkspaceError, match="absolute path"):
        workspace.read("/etc/passwd")


def test_a_symlink_out_of_the_project_is_refused(
    workspace: Workspace, project: Path
) -> None:
    link = project / "escape.txt"
    os.symlink(project.parent / "outside.txt", link)

    with pytest.raises(WorkspaceError, match="outside the project"):
        workspace.read("escape.txt")


def test_symlinks_are_not_listed(workspace: Workspace, project: Path) -> None:
    os.symlink(project.parent / "outside.txt", project / "escape.txt")

    assert "escape.txt" not in [entry.path for entry in workspace.tree()]


def test_an_empty_path_is_refused(workspace: Workspace) -> None:
    with pytest.raises(WorkspaceError, match="no path given"):
        workspace.read("   ")


def test_opening_a_missing_directory_is_reported(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="project directory not found"):
        Workspace.open(tmp_path / "nope")


# ---- files that are never reachable ------------------------------------


@pytest.mark.parametrize("name", [".env", "server.key"])
def test_credential_files_are_refused_by_name(workspace: Workspace, name: str) -> None:
    with pytest.raises(WorkspaceError, match="never readable"):
        workspace.read(name)


def test_credential_files_are_not_listed(workspace: Workspace) -> None:
    listed = [entry.path for entry in workspace.tree()]

    assert ".env" not in listed
    assert "server.key" not in listed


def test_excluded_directories_are_not_listed(workspace: Workspace) -> None:
    listed = [entry.path for entry in workspace.tree()]

    assert not any(path.startswith(".git") for path in listed)
    assert not any(path.startswith("node_modules") for path in listed)


def test_reading_inside_an_excluded_directory_is_refused(
    workspace: Workspace,
) -> None:
    with pytest.raises(WorkspaceError, match="excluded directory"):
        workspace.read(".git/config")


# ---- listing -----------------------------------------------------------


def test_the_tree_lists_project_files(workspace: Workspace) -> None:
    listed = {entry.path for entry in workspace.tree()}

    assert "README.md" in listed
    assert "src" in listed
    assert "src/main.py" in listed


def test_the_tree_is_capped(workspace: Workspace, project: Path) -> None:
    for index in range(50):
        (project / f"file{index}.txt").write_text("x", encoding="utf-8")

    assert len(workspace.tree(limit=10)) == 10


def test_directories_are_marked_as_such(workspace: Workspace) -> None:
    entries = {entry.path: entry for entry in workspace.tree()}

    assert entries["src"].is_dir
    assert not entries["src/main.py"].is_dir
    assert entries["src/main.py"].size > 0


# ---- reading -----------------------------------------------------------


def test_reading_a_file(workspace: Workspace) -> None:
    content = workspace.read("src/main.py")

    assert content.path == "src/main.py"
    assert content.text == "print('hi')\n"
    assert content.lines == 2


def test_a_directory_is_not_a_file(workspace: Workspace) -> None:
    with pytest.raises(WorkspaceError, match="is not a file"):
        workspace.read("src")


def test_an_oversized_file_is_refused(workspace: Workspace, project: Path) -> None:
    (project / "huge.txt").write_text("x" * (MAX_FILE_BYTES + 1), encoding="utf-8")

    with pytest.raises(WorkspaceError, match="the limit is"):
        workspace.read("huge.txt")


def test_a_binary_file_is_refused(workspace: Workspace, project: Path) -> None:
    (project / "sheet.xlsx").write_bytes(b"PK\x03\x04\x00\x00binary")

    with pytest.raises(WorkspaceError, match="binary file"):
        workspace.read("sheet.xlsx")


def test_invalid_utf8_is_refused(workspace: Workspace, project: Path) -> None:
    (project / "latin.txt").write_bytes(b"caf\xe9 no null byte here")

    with pytest.raises(WorkspaceError, match="not valid UTF-8"):
        workspace.read("latin.txt")


# ---- the credential scan -----------------------------------------------


def test_a_file_holding_a_credential_is_not_returned(
    workspace: Workspace, project: Path
) -> None:
    (project / "config.py").write_text(
        f"HOST = 'localhost'\nTOKEN = '{FAKE_KEY}'\n", encoding="utf-8"
    )

    with pytest.raises(WorkspaceSecretError) as caught:
        workspace.read("config.py")

    message = str(caught.value)
    assert "line 2" in message
    assert "OpenAI-style API key" in message
    assert "cannot be recalled" in message
    assert FAKE_KEY not in message


def test_a_placeholder_does_not_block_a_file(
    workspace: Workspace, project: Path
) -> None:
    (project / "settings.py").write_text(
        "API_KEY = 'your-api-key-here'\n", encoding="utf-8"
    )

    assert "your-api-key-here" in workspace.read("settings.py").text
