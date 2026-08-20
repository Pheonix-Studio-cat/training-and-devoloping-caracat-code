"""Tests for reading and changing GitHub repositories.

The network is stubbed at :func:`caracat_code.github._request`, so these cover
the decisions this module makes -- which hosts, which paths, which files, and
what is refused -- rather than GitHub's behaviour, which is not ours to test.

The refusals are the point, so most of these are attempts to get past one.
"""

from __future__ import annotations

import json

import pytest

from caracat_code.github import (
    API_HOST,
    GitHubError,
    GitHubSecretError,
    ProposedChange,
    RepoRef,
    _request,
    list_tree,
    open_pull_request,
    parse_repo,
    read_file,
)

REPO = RepoRef(owner="Pheonix-Studio-cat", name="training-and-devoloping-caracat-code")

FAKE_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"


def tree_payload(*entries: tuple[str, int]) -> bytes:
    return json.dumps(
        {"tree": [{"path": p, "type": "blob", "size": s} for p, s in entries]}
    ).encode()


class Recorder(list):
    """Every request the module would make, answered from a script.

    A list so a test can index into the calls, with the queued replies hanging
    off it -- the two are always read together.
    """

    def __init__(self) -> None:
        super().__init__()
        self.replies: list[bytes] = []


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorded = Recorder()

    def fake(url, *, token=None, method="GET", payload=None):
        recorded.append(
            {"url": url, "token": token, "method": method, "payload": payload}
        )
        return recorded.replies.pop(0) if recorded.replies else b"{}"

    monkeypatch.setattr("caracat_code.github._request", fake)
    return recorded


# ---- naming a repository -----------------------------------------------


def test_a_plain_owner_and_name_is_accepted() -> None:
    repo = parse_repo("Pheonix-Studio-cat/training-and-devoloping-caracat-code")

    assert repo.owner == "Pheonix-Studio-cat"
    assert repo.ref == "main"


def test_a_branch_can_be_named() -> None:
    assert parse_repo("owner/name@release-2").ref == "release-2"


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("https://github.com/a/b", "looks like a URL"),
        ("github.com/a/b", "looks like a URL"),
        ("justaname", "owner/name"),
        ("a/b/c", "owner/name"),
        ("-nope/name", "usable GitHub owner"),
        ("owner/-nope", "usable GitHub repository name"),
        ("", "no repository given"),
    ],
)
def test_an_unusable_repository_is_refused_with_a_reason(
    spec: str, message: str
) -> None:
    with pytest.raises(GitHubError, match=message):
        parse_repo(spec)


# ---- the fixed hosts ---------------------------------------------------


def test_no_host_outside_github_can_be_called() -> None:
    """The guarantee that keeps this from becoming an open proxy."""
    with pytest.raises(GitHubError, match="outside GitHub"):
        _request("https://evil.example/repos/a/b", token=None)


def test_the_cloud_metadata_address_is_not_reachable_either() -> None:
    with pytest.raises(GitHubError, match="outside GitHub"):
        _request("http://169.254.169.254/latest/meta-data/", token=None)


# ---- listing a tree ----------------------------------------------------


def test_the_tree_is_fetched_in_one_request(calls: Recorder) -> None:
    calls.replies.append(tree_payload(("README.md", 10), ("src/app.py", 20)))

    entries = list_tree(REPO)

    assert [e.path for e in entries] == ["README.md", "src/app.py"]
    assert len(calls) == 1
    assert calls[0]["url"].startswith(f"https://{API_HOST}/repos/")
    assert "recursive=1" in calls[0]["url"]


def test_excluded_directories_are_not_listed(calls: Recorder) -> None:
    calls.replies.append(
        tree_payload(
            ("app.py", 10),
            ("node_modules/left-pad/index.js", 10),
            (".git/config", 10),
            ("__pycache__/app.cpython-311.pyc", 10),
        )
    )

    assert [e.path for e in list_tree(REPO)] == ["app.py"]


def test_credential_shaped_filenames_are_not_listed(
    calls: Recorder,
) -> None:
    """Refused by name, before anyone can click on them."""
    calls.replies.append(
        tree_payload(("app.py", 10), (".env", 10), ("deploy/id_rsa", 10))
    )

    assert [e.path for e in list_tree(REPO)] == ["app.py"]


def test_binaries_and_oversized_files_are_not_listed(
    calls: Recorder,
) -> None:
    calls.replies.append(
        tree_payload(("logo.png", 10), ("app.py", 10), ("huge.py", 999_999))
    )

    assert [e.path for e in list_tree(REPO)] == ["app.py"]


# ---- reading a file ----------------------------------------------------


def test_a_file_is_read_from_the_cdn(calls: Recorder) -> None:
    calls.replies.append(b"print('hello')\n")

    found = read_file(REPO, "src/app.py")

    assert found.text == "print('hello')\n"
    assert found.repo == REPO.slug
    assert "raw.githubusercontent.com" in calls[0]["url"]


def test_a_file_holding_a_key_is_refused(calls: Recorder) -> None:
    """Public does not mean harmless: sending it onward cannot be undone."""
    calls.replies.append(f"TOKEN = '{FAKE_KEY}'\n".encode())

    with pytest.raises(GitHubSecretError) as caught:
        read_file(REPO, "settings.py")

    assert "line 1" in str(caught.value)
    assert FAKE_KEY not in str(caught.value)


def test_a_binary_file_is_refused(calls: Recorder) -> None:
    calls.replies.append(b"\x89PNG\r\n\x1a\n\x00\x00")

    with pytest.raises(GitHubError, match="binary"):
        read_file(REPO, "logo.png")


@pytest.mark.parametrize(
    "path",
    ["../../etc/passwd", "/etc/passwd", "a/../../b", "./../x", "..", "   "],
)
def test_a_path_cannot_leave_the_repository(path: str, calls: Recorder) -> None:
    """Refused, not repaired -- and refused before anything is requested."""
    with pytest.raises(GitHubError, match=r"stay inside|no file path"):
        read_file(REPO, path)

    assert calls == [], "the path was rejected only after asking GitHub"


# ---- changing a repository ---------------------------------------------


def test_changing_anything_needs_a_token() -> None:
    with pytest.raises(GitHubError, match="needs a GitHub token"):
        open_pull_request(
            REPO,
            [ProposedChange("a.py", "x = 1\n")],
            title="t",
            body="b",
            token="",
            branch="caracat/change",
        )


def test_the_default_branch_cannot_be_written_to(
    calls: Recorder,
) -> None:
    """The refusal this module exists to make structural."""
    calls.replies.append(json.dumps({"default_branch": "main"}).encode())

    with pytest.raises(GitHubError, match="refusing to write to 'main'"):
        open_pull_request(
            REPO,
            [ProposedChange("a.py", "x = 1\n")],
            title="t",
            body="b",
            token="ghp_x",
            branch="main",
        )


def test_a_change_carrying_a_key_is_never_pushed(
    calls: Recorder,
) -> None:
    calls.replies.append(json.dumps({"default_branch": "main"}).encode())

    with pytest.raises(GitHubSecretError):
        open_pull_request(
            REPO,
            [ProposedChange("settings.py", f"KEY = '{FAKE_KEY}'\n")],
            title="t",
            body="b",
            token="ghp_x",
            branch="caracat/change",
        )

    # Only the default-branch lookup happened: nothing was created.
    assert all(call["method"] == "GET" for call in calls)


def test_too_many_files_are_refused() -> None:
    with pytest.raises(GitHubError, match="should carry"):
        open_pull_request(
            REPO,
            [ProposedChange(f"f{n}.py", "x = 1\n") for n in range(30)],
            title="t",
            body="b",
            token="ghp_x",
            branch="caracat/change",
        )


def test_a_change_becomes_a_branch_and_a_pull_request(
    calls: Recorder,
) -> None:
    calls.replies.extend(
        [
            json.dumps({"default_branch": "main"}).encode(),
            json.dumps({"object": {"sha": "a" * 40}}).encode(),
            b"{}",  # create the branch
            json.dumps({"sha": "b" * 40}).encode(),  # the file already exists
            b"{}",  # write it
            json.dumps({"html_url": "https://github.com/o/r/pull/7"}).encode(),
        ]
    )

    url = open_pull_request(
        REPO,
        [ProposedChange("README.md", "# new\n")],
        title="Improve the readme",
        body="why",
        token="ghp_x",
        branch="caracat/readme",
    )

    assert url == "https://github.com/o/r/pull/7"
    methods = [(c["method"], str(c["url"]).rsplit("/", 2)[-2:]) for c in calls]
    assert ("POST", ["git", "refs"]) in [(m, u) for m, u in methods]
    assert any(c["method"] == "PUT" for c in calls)
    assert calls[-1]["method"] == "POST"
    assert str(calls[-1]["url"]).endswith("/pulls")
    assert calls[-1]["payload"]["base"] == "main"
    assert calls[-1]["payload"]["head"] == "caracat/readme"
