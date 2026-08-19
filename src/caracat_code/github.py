"""Reading and changing GitHub repositories, from a fixed pair of hosts.

Caracat Code needs to see the code being discussed. On a machine that is a
project directory; on a tablet there is none, and the code lives on GitHub
anyway. This module is that second path.

**Two hosts, written down here, never supplied by a caller.** Everything goes to
``api.github.com`` or ``raw.githubusercontent.com``. A module that took a host
from its caller would be an open proxy wearing a GitHub label, so this one does
not have that shape at all -- the same rule ``fetch.py`` is built on, applied
harder because here there is nothing legitimate to point elsewhere.

**Reading is cheap on purpose.** The whole file tree of a repository arrives in
one API call, and file contents come from the raw CDN, which does not consume
the API's hourly allowance. Browsing a repository therefore costs one request,
not one per file.

**Writing never touches the default branch.** A change becomes a branch and a
pull request: reviewable before it lands, revertible after. There is no function
here that commits to ``main``, so no caller can decide otherwise.

**Everything sent onwards is scanned first.** A key committed to a public
repository is public the moment it lands, and rotation is the only cure. So the
same scanner the training data uses runs over every file read out and every file
written back.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from fnmatch import fnmatch

from caracat_code.data_prep import SecretFinding, scan_for_secrets
from caracat_code.interface import redact
from caracat_code.workspace import EXCLUDED_DIRECTORIES, NEVER_READABLE

__all__ = [
    "API_HOST",
    "RAW_HOST",
    "GitHubError",
    "GitHubSecretError",
    "ProposedChange",
    "RepoEntry",
    "RepoFile",
    "RepoRef",
    "list_tree",
    "open_pull_request",
    "parse_repo",
    "read_file",
]

API_HOST = "api.github.com"
RAW_HOST = "raw.githubusercontent.com"
"""The only two hosts this module talks to. Not configurable, by design."""

MAX_FILE_BYTES = 256 * 1024
"""Matches the project-directory limit: what is too big to quote there is too
big to quote from here."""

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
"""A whole tree is legitimately large; a runaway response is not."""

MAX_LISTED_ENTRIES = 3000
MAX_CHANGED_FILES = 20
"""One proposal should be reviewable. Beyond this it is a rewrite, not a change."""

TIMEOUT_SECONDS = 20

# GitHub's own rule for owner and repository names, written out rather than
# approximated: letters, digits, hyphen, underscore and dot, and neither end may
# be a dot or a hyphen.
_NAME = re.compile(r"^[A-Za-z0-9_](?:[A-Za-z0-9._-]*[A-Za-z0-9_])?$")

# A branch name this project creates. Deliberately narrow -- it ends up in a URL
# and in a git ref, and both have opinions about what may appear there.
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,98}[A-Za-z0-9]$")

TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".md",
        ".rst",
        ".txt",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
        ".html",
        ".css",
        ".scss",
        ".sh",
        ".bash",
        ".sql",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".xml",
        ".csv",
        ".env.example",
        ".gitignore",
        ".dockerignore",
        "Dockerfile",
        "Makefile",
        "LICENSE",
        "NOTICE",
    }
)
"""What is worth offering to attach. A repository holds images and archives too,
and listing them would bury the files someone actually wants to talk about."""


class GitHubError(ValueError):
    """Raised when a repository, path or response cannot be used."""


class GitHubSecretError(GitHubError):
    """Raised when content holds something credential-shaped.

    Separate from :class:`GitHubError` because the caller must not treat it as a
    transient failure to retry past.
    """


@dataclass(frozen=True)
class RepoRef:
    """One repository at one branch."""

    owner: str
    name: str
    ref: str = "main"

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"

    def __str__(self) -> str:
        return f"{self.slug}@{self.ref}"


@dataclass(frozen=True)
class RepoEntry:
    """One file in a repository tree."""

    path: str
    size: int


@dataclass(frozen=True)
class RepoFile:
    """The text of one repository file, checked before it travels further."""

    repo: str
    path: str
    text: str
    lines: int


@dataclass(frozen=True)
class ProposedChange:
    """One file a change would write. Not applied until a person says so."""

    path: str
    text: str


def parse_repo(spec: str, *, default_ref: str = "main") -> RepoRef:
    """Turn ``owner/name`` or ``owner/name@branch`` into a :class:`RepoRef`.

    Raises:
        GitHubError: If the shape is wrong. The message says what was expected,
            because the most common mistakes -- a pasted URL, a bare name -- are
            worth naming rather than rejecting silently.
    """
    if not isinstance(spec, str) or not spec.strip():
        raise GitHubError("no repository given; expected owner/name")

    text = spec.strip()
    if "://" in text or text.startswith("github.com"):
        raise GitHubError(
            f"{text!r} looks like a URL. Use just the owner and name, for "
            "example Pheonix-Studio-cat/training-and-devoloping-caracat-code"
        )

    ref = default_ref
    if "@" in text:
        text, _, ref = text.partition("@")
        if not _BRANCH.match(ref):
            raise GitHubError(f"{ref!r} is not a usable branch name")

    parts = text.split("/")
    if len(parts) != 2:
        raise GitHubError(
            f"{spec!r} should be owner/name -- two parts separated by one slash"
        )

    owner, name = parts
    for part, label in ((owner, "owner"), (name, "repository name")):
        if not _NAME.match(part):
            raise GitHubError(f"{part!r} is not a usable GitHub {label}")

    return RepoRef(owner=owner, name=name, ref=ref)


def _check_path(path: str) -> str:
    """A path inside a repository, or an explanation of why it is not one.

    The checks run on the text as given. An earlier version stripped leading
    ``./`` with ``lstrip("./")``, which removes those *characters* rather than
    that *prefix* -- so ``../../etc/passwd`` quietly became ``etc/passwd`` and
    passed a test for traversal it should have failed. A path that looks like an
    escape attempt is refused, never repaired.
    """
    if not isinstance(path, str) or not path.strip():
        raise GitHubError("no file path given")

    cleaned = path.strip()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]

    if cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise GitHubError(f"{path!r} does not stay inside the repository")
    if "\\" in cleaned or "\0" in cleaned:
        raise GitHubError(f"{path!r} contains characters a repository path cannot")
    if not cleaned:
        raise GitHubError("no file path given")
    return cleaned


def _is_interesting(path: str) -> bool:
    """Whether a tree entry is worth offering to attach."""
    parts = path.split("/")
    if any(part in EXCLUDED_DIRECTORIES for part in parts[:-1]):
        return False
    name = parts[-1]
    if any(fnmatch(name, pattern) for pattern in NEVER_READABLE):
        return False
    if name in TEXT_SUFFIXES:
        return True
    return any(name.endswith(suffix) for suffix in TEXT_SUFFIXES if suffix[0] == ".")


def _request(
    url: str,
    *,
    token: str | None,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> bytes:
    """One call to a host this module chose. Errors never carry the token."""
    if urllib.parse.urlsplit(url).hostname not in {API_HOST, RAW_HOST}:
        # Unreachable through the public functions; here so it stays unreachable
        # if someone adds one that builds a URL less carefully.
        raise GitHubError("refusing to call a host outside GitHub")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "caracat-code",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read(MAX_RESPONSE_BYTES + 1)[:MAX_RESPONSE_BYTES]
    except urllib.error.HTTPError as exc:
        detail = redact(exc.read(2000).decode("utf-8", "replace"), token or "")
        raise GitHubError(_explain(exc.code, detail)) from None
    except urllib.error.URLError as exc:
        raise GitHubError(f"could not reach {API_HOST}: {exc.reason}") from None


def _explain(status: int, detail: str) -> str:
    """Turn a status code into something worth reading."""
    if status == 404:
        return (
            "GitHub says that does not exist. For a public repository, check the "
            f"owner and name; a private one is not reachable without a token. {detail}"
        )
    if status in (401, 403):
        if "rate limit" in detail.lower():
            return (
                "GitHub's hourly allowance for unauthenticated requests is used "
                "up. It refills on the hour, or a token raises the limit. "
                f"{detail}"
            )
        return f"GitHub refused the request ({status}). {detail}"
    if status == 422:
        return f"GitHub rejected the contents of the request. {detail}"
    return f"GitHub returned {status}. {detail}"


def list_tree(
    repo: RepoRef, *, token: str | None = None, limit: int = MAX_LISTED_ENTRIES
) -> list[RepoEntry]:
    """Every attachable file in ``repo``, in one request.

    Directories, excluded folders, credential-shaped filenames and binary
    formats are dropped here rather than shown and refused later.
    """
    url = (
        f"https://{API_HOST}/repos/{repo.owner}/{repo.name}"
        f"/git/trees/{urllib.parse.quote(repo.ref, safe='')}?recursive=1"
    )
    data = json.loads(_request(url, token=token) or b"{}")

    entries = [
        RepoEntry(path=item["path"], size=int(item.get("size") or 0))
        for item in data.get("tree", [])
        if item.get("type") == "blob"
        and _is_interesting(item.get("path", ""))
        and int(item.get("size") or 0) <= MAX_FILE_BYTES
    ]
    entries.sort(key=lambda entry: entry.path)
    return entries[:limit]


def read_file(repo: RepoRef, path: str, *, token: str | None = None) -> RepoFile:
    """One file's text, refused if it holds something credential-shaped.

    Raises:
        GitHubError: If the path is unusable, the file is too big or binary.
        GitHubSecretError: If it looks like it holds a credential. Public does
            not mean harmless -- forwarding it to an inference provider is a
            second disclosure, and one that cannot be undone.
    """
    clean = _check_path(path)
    url = (
        f"https://{RAW_HOST}/{repo.owner}/{repo.name}/"
        f"{urllib.parse.quote(repo.ref, safe='')}/"
        f"{urllib.parse.quote(clean)}"
    )
    raw = _request(url, token=token)

    if len(raw) > MAX_FILE_BYTES:
        raise GitHubError(
            f"{clean} is larger than {MAX_FILE_BYTES} bytes. Point at the part "
            "you care about instead."
        )
    if b"\0" in raw[:8192]:
        raise GitHubError(f"{clean} looks like a binary file, so there is no text")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubError(f"{clean} is not valid UTF-8 text: {exc.reason}") from None

    _refuse_if_credential_shaped(text, clean)
    return RepoFile(repo=repo.slug, path=clean, text=text, lines=len(text.splitlines()))


def _refuse_if_credential_shaped(text: str, label: str) -> None:
    findings: list[SecretFinding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        findings.extend(scan_for_secrets(line, line_number=number, field_name=label))
        if findings:
            break
    if findings:
        raise GitHubSecretError(
            f"{label} was not used: {findings[0].describe()}. The value is not "
            "repeated here on purpose."
        )


# ---- changing a repository ---------------------------------------------
#
# Every path below ends at a pull request. There is deliberately no function
# that writes to the default branch: the guarantee is structural, not a rule
# someone has to remember.


def _default_branch(repo: RepoRef, token: str) -> str:
    url = f"https://{API_HOST}/repos/{repo.owner}/{repo.name}"
    return str(
        json.loads(_request(url, token=token) or b"{}").get("default_branch") or "main"
    )


def _head_sha(repo: RepoRef, branch: str, token: str) -> str:
    url = (
        f"https://{API_HOST}/repos/{repo.owner}/{repo.name}"
        f"/git/ref/heads/{urllib.parse.quote(branch, safe='')}"
    )
    data = json.loads(_request(url, token=token) or b"{}")
    sha = (data.get("object") or {}).get("sha")
    if not sha:
        raise GitHubError(f"could not find the tip of {branch!r} in {repo.slug}")
    return str(sha)


def _existing_sha(repo: RepoRef, path: str, branch: str, token: str) -> str | None:
    """The blob sha of a file, or ``None`` when it is new.

    GitHub needs the current sha to replace a file, and refuses it for one that
    does not exist yet -- so the two cases have to be told apart first.
    """
    url = (
        f"https://{API_HOST}/repos/{repo.owner}/{repo.name}"
        f"/contents/{urllib.parse.quote(path)}"
        f"?ref={urllib.parse.quote(branch, safe='')}"
    )
    try:
        data = json.loads(_request(url, token=token) or b"{}")
    except GitHubError as exc:
        if "does not exist" in str(exc):
            return None
        raise
    sha = data.get("sha")
    return str(sha) if sha else None


def open_pull_request(
    repo: RepoRef,
    changes: list[ProposedChange],
    *,
    title: str,
    body: str,
    token: str,
    branch: str,
) -> str:
    """Put ``changes`` on a new branch and open a pull request for them.

    Nothing here decides to run: the caller reaches this function only after a
    person has looked at the change and asked for it.

    Returns:
        The pull request's URL.

    Raises:
        GitHubError: If the request is unusable or GitHub refuses it.
        GitHubSecretError: If any new content looks like it holds a credential.
    """
    if not token:
        raise GitHubError(
            "changing a repository needs a GitHub token with Contents and Pull "
            "requests permission for exactly this repository"
        )
    if not changes:
        raise GitHubError("there is nothing to change")
    if len(changes) > MAX_CHANGED_FILES:
        raise GitHubError(
            f"{len(changes)} files is more than one pull request should carry "
            f"(the limit is {MAX_CHANGED_FILES}). Split it up."
        )
    if not _BRANCH.match(branch):
        raise GitHubError(f"{branch!r} is not a usable branch name")

    base = _default_branch(repo, token)
    if branch == base:
        # The one refusal that matters most, stated where it happens.
        raise GitHubError(
            f"refusing to write to {base!r} directly. Changes go on their own "
            "branch and through a pull request, so they can be read before they "
            "land and undone after."
        )

    prepared = []
    for change in changes:
        path = _check_path(change.path)
        _refuse_if_credential_shaped(change.text, path)
        prepared.append((path, change.text))

    _request(
        f"https://{API_HOST}/repos/{repo.owner}/{repo.name}/git/refs",
        token=token,
        method="POST",
        payload={"ref": f"refs/heads/{branch}", "sha": _head_sha(repo, base, token)},
    )

    for path, text in prepared:
        payload: dict[str, object] = {
            "message": f"{title}\n\nProposed by Caracat Code; reviewed before merge.",
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        existing = _existing_sha(repo, path, branch, token)
        if existing:
            payload["sha"] = existing
        _request(
            f"https://{API_HOST}/repos/{repo.owner}/{repo.name}"
            f"/contents/{urllib.parse.quote(path)}",
            token=token,
            method="PUT",
            payload=payload,
        )

    opened = json.loads(
        _request(
            f"https://{API_HOST}/repos/{repo.owner}/{repo.name}/pulls",
            token=token,
            method="POST",
            payload={"title": title, "body": body, "head": branch, "base": base},
        )
        or b"{}"
    )
    url = opened.get("html_url")
    if not url:
        raise GitHubError("GitHub accepted the branch but returned no pull request")
    return str(url)
