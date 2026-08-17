"""Reading files from one project directory, and only from there.

This is what lets the assistant talk about your actual code instead of an
invented example. It is also the part where a mistake is expensive, so the rules
are narrow on purpose:

- **One root.** The server is started with a single directory. Every path is
  resolved and must land inside it. Resolving follows symlinks, so a link
  pointing outside the project resolves outside and is refused.
- **Some files are never reachable**, by name, before anything else is checked:
  ``.env``, private keys, credential stores. There is no legitimate reason to
  send those to a language model.
- **Everything else is scanned before it leaves.** Sending a project file to a
  provider means it leaves your machine; a key that goes with it cannot be
  called back. The scanner from :mod:`caracat_code.data_prep` is reused, so
  there is one definition of "this looks like a credential" in the project.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from caracat_code.data_prep import SecretFinding, scan_for_secrets

__all__ = [
    "EXCLUDED_DIRECTORIES",
    "MAX_FILE_BYTES",
    "MAX_LISTED_ENTRIES",
    "NEVER_READABLE",
    "FileContent",
    "Workspace",
    "WorkspaceEntry",
    "WorkspaceError",
    "WorkspaceSecretError",
]

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".next",
        ".tox",
    }
)

NEVER_READABLE = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "credentials.json",
    "secrets.yaml",
    "secrets.yml",
    ".npmrc",
    ".pypirc",
    ".netrc",
)
"""Refused by name, before size, type or content is considered."""

MAX_FILE_BYTES = 256 * 1024
MAX_COPY_BYTES = 16 * 1024 * 1024
"""Larger than MAX_FILE_BYTES: a copy stays on this machine, a read does not."""

MAX_LISTED_ENTRIES = 2000
BINARY_SNIFF_BYTES = 4096


class WorkspaceError(ValueError):
    """Raised when a path is outside the project or otherwise unusable."""


class WorkspaceSecretError(WorkspaceError):
    """Raised when a file holds something that looks like a credential."""

    def __init__(self, path: str, findings: list[SecretFinding]) -> None:
        listed = "\n".join(f"  - {finding.describe()}" for finding in findings)
        super().__init__(
            f"{path} was not read: it contains {len(findings)} possible "
            f"credential(s).\n{listed}\n\n"
            "Sending this file to a provider would send the credential with it, "
            "and an API request cannot be recalled. Remove or replace the value "
            "first. The matched values are deliberately not shown here."
        )
        self.path = path
        self.findings = tuple(findings)


@dataclass(frozen=True)
class WorkspaceEntry:
    """One file or directory, described relative to the project root."""

    path: str
    is_dir: bool
    size: int = 0


@dataclass(frozen=True)
class FileContent:
    """The readable text of one project file."""

    path: str
    text: str
    lines: int
    truncated: bool = False


def _is_never_readable(name: str) -> bool:
    return any(fnmatch(name, pattern) for pattern in NEVER_READABLE)


@dataclass(frozen=True)
class Workspace:
    """A single project directory the assistant may read from."""

    root: Path

    @classmethod
    def open(cls, path: str | Path) -> Workspace:
        """Open ``path`` as the project root.

        Raises:
            WorkspaceError: If it is not an existing directory.
        """
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise WorkspaceError(f"project directory not found: {root}")
        return cls(root=root)

    # ---- the security core ---------------------------------------------

    def resolve(self, relative: str) -> Path:
        """Turn a path from the browser into a real path inside the project.

        Raises:
            WorkspaceError: If it escapes the root, names an excluded
                directory, or is one of the files that are never readable.
        """
        if not isinstance(relative, str) or not relative.strip():
            raise WorkspaceError("no path given")

        candidate = Path(relative)
        if candidate.is_absolute():
            raise WorkspaceError(
                f"{relative!r} is an absolute path; only paths inside the "
                "project directory can be opened"
            )

        resolved = (self.root / candidate).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise WorkspaceError(
                f"{relative!r} resolves outside the project directory. Only "
                f"files under {self.root} can be opened."
            )

        parts = resolved.relative_to(self.root).parts
        for part in parts[:-1]:
            if part in EXCLUDED_DIRECTORIES:
                raise WorkspaceError(f"{relative!r} is inside an excluded directory")
        if parts and _is_never_readable(parts[-1]):
            raise WorkspaceError(
                f"{parts[-1]} is never readable: files of this kind hold "
                "credentials, and there is no good reason to send one to a "
                "language model."
            )
        return resolved

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    # ---- listing and reading -------------------------------------------

    def tree(self, limit: int = MAX_LISTED_ENTRIES) -> list[WorkspaceEntry]:
        """List the project, skipping excluded directories and hidden clutter.

        Sorted and capped, so a huge checkout cannot flood the interface.
        """
        entries: list[WorkspaceEntry] = []

        def walk(directory: Path) -> None:
            if len(entries) >= limit:
                return
            try:
                children = sorted(
                    directory.iterdir(), key=lambda item: (item.is_file(), item.name)
                )
            except OSError:
                return
            for child in children:
                if len(entries) >= limit:
                    return
                if child.is_symlink():
                    continue  # a link can point anywhere; do not offer it
                if child.is_dir():
                    if child.name in EXCLUDED_DIRECTORIES:
                        continue
                    entries.append(
                        WorkspaceEntry(path=self.relative(child), is_dir=True)
                    )
                    walk(child)
                elif child.is_file():
                    if _is_never_readable(child.name):
                        continue
                    try:
                        size = child.stat().st_size
                    except OSError:
                        continue
                    entries.append(
                        WorkspaceEntry(
                            path=self.relative(child), is_dir=False, size=size
                        )
                    )

        walk(self.root)
        return entries

    def read_binary(self, relative: str, max_bytes: int = MAX_COPY_BYTES) -> bytes:
        """Read a file's raw bytes, for copying into a local sandbox run.

        The credential scan deliberately does **not** apply here, and the reason
        matters: that scan exists to stop a file leaving the machine on its way
        to a provider. Copying a file into a sandbox directory on the same
        machine is not a disclosure, and refusing binary files would rule out
        exactly the spreadsheets and archives this is for.

        The name check and the size cap still apply, so ``.env`` and private
        keys stay unreachable by this route too.

        Raises:
            WorkspaceError: If the path is not readable or is too large.
        """
        path = self.resolve(relative)
        if not path.is_file():
            raise WorkspaceError(f"{relative!r} is not a file")

        size = path.stat().st_size
        if size > max_bytes:
            raise WorkspaceError(
                f"{relative} is {size} bytes, and at most {max_bytes} can be "
                "copied into a run."
            )
        return path.read_bytes()

    def read(self, relative: str) -> FileContent:
        """Read one project file as text, after checking it is safe to send.

        Raises:
            WorkspaceError: If the path is not readable, too large or binary.
            WorkspaceSecretError: If the file holds something credential-shaped.
        """
        path = self.resolve(relative)

        if not path.is_file():
            raise WorkspaceError(f"{relative!r} is not a file")

        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise WorkspaceError(
                f"{relative} is {size} bytes, the limit is {MAX_FILE_BYTES}. "
                "Open a smaller file, or point at the part you care about."
            )

        raw = path.read_bytes()
        if b"\0" in raw[:BINARY_SNIFF_BYTES]:
            raise WorkspaceError(
                f"{relative} looks like a binary file, so there is no text to "
                "read. A spreadsheet or an image has to be handled by code, not "
                "quoted into a conversation."
            )

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(
                f"{relative} is not valid UTF-8 text: {exc.reason}"
            ) from exc

        # Scanned line by line so a finding can name the line to go and fix.
        findings: list[SecretFinding] = []
        for number, line in enumerate(text.splitlines(), start=1):
            findings.extend(
                scan_for_secrets(line, line_number=number, field_name=relative)
            )
        if findings:
            raise WorkspaceSecretError(relative, findings)

        return FileContent(
            path=self.relative(path), text=text, lines=text.count("\n") + 1
        )
