"""Running Python code under resource limits, on copies of your files.

This is what turns "here is a script that should work" into "here is what
happened when it ran". It is also the most dangerous thing in the project, so
the limits are explicit and so are their gaps.

**What is enforced**

- a wall-clock timeout, and a CPU-time limit below it;
- an address-space limit, so a runaway allocation dies instead of the machine;
- a file-size limit, which also caps how much the program can print;
- a limit on open file descriptors;
- a fresh temporary directory as the working directory, deleted afterwards;
- an environment built from nothing, so ``CARACAT_API_KEY`` and every other
  secret in your shell are simply absent;
- its own process group, so a program that spawns children still gets killed.

**What is not enforced, stated plainly**

This is not a container. The code runs as your user. It can reach the network,
and it can read files your account can read. Resource limits stop a runaway
program; they do not stop a hostile one.

Code you do not understand does not belong here. Say so, out loud, wherever
this is offered.

**Your files are copied, not opened.** Anything named for the run is copied into
the temporary directory first, so a wrong script destroys a copy and leaves the
original alone. Files the program produced are listed afterwards, to be fetched
back deliberately.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "RESERVED_PREFIX",
    "RunResult",
    "SandboxError",
    "SandboxLimits",
    "run_python",
]

RESERVED_PREFIX = "_caracat_"
"""Every file the sandbox writes carries this prefix.

Without it the sandbox would write its own program to ``main.py`` -- and a
project file of that very common name, copied in for the run, would be silently
replaced by it. Reserving a prefix makes the collision impossible instead of
unlikely, and leaves ordinary names free for your own files.
"""

MAX_CODE_CHARS = 200_000

LIMIT_SIGNALS: dict[int, str] = {
    int(signal.SIGKILL): "it was killed outright, which is what the memory and "
    "CPU ceilings do when they are reached",
    int(signal.SIGXCPU): "it used up its CPU-time allowance",
    int(signal.SIGXFSZ): "it wrote more than the file-size allowance, which also "
    "caps how much it can print",
}
"""Signals that mean "a limit stopped this", not "the program crashed".

Without this distinction a program stopped by the sandbox is reported as exit
code -9, which reads like a crash and tells the person nothing.
"""


class SandboxError(ValueError):
    """Raised when a run cannot be started at all."""


@dataclass(frozen=True)
class SandboxLimits:
    """The ceilings a run is held to. Lower is safer, not slower."""

    timeout_seconds: float = 10.0
    memory_mb: int = 512
    max_output_chars: int = 20_000
    max_file_mb: int = 16
    max_open_files: int = 64

    def validate(self) -> None:
        if not 0 < self.timeout_seconds <= 300:
            raise SandboxError("timeout must be between 0 and 300 seconds")
        if not 16 <= self.memory_mb <= 8192:
            raise SandboxError("memory limit must be between 16 and 8192 MB")
        if self.max_output_chars < 1:
            raise SandboxError("output limit must be positive")


@dataclass(frozen=True)
class RunResult:
    """What happened. ``exit_code`` is ``None`` when the run was killed."""

    stdout: str
    stderr: str
    exit_code: int | None
    duration_seconds: float
    timed_out: bool = False
    output_truncated: bool = False
    produced_files: tuple[str, ...] = field(default_factory=tuple)
    """Files that are new or whose contents changed -- what is worth fetching
    back. An input the program only read is not listed."""

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def stopped_by_limit(self) -> bool:
        """Whether the sandbox stopped this run, rather than the program ending.

        True for the wall-clock timeout and for a kill by one of the resource
        ceilings. Which of the two fires first is a race when a program burns
        CPU as fast as it can, so both have to count.
        """
        if self.timed_out:
            return True
        return self.exit_code is not None and -self.exit_code in LIMIT_SIGNALS


RUNNER_SOURCE = """\
# Written by caracat_code.sandbox. Sets the limits from inside the child, which
# is safe in a threaded parent -- unlike subprocess's preexec_fn.
import resource
import runpy
import sys

resource.setrlimit(resource.RLIMIT_AS, ({memory_bytes}, {memory_bytes}))
resource.setrlimit(resource.RLIMIT_CPU, ({cpu_seconds}, {cpu_seconds}))
resource.setrlimit(resource.RLIMIT_FSIZE, ({file_bytes}, {file_bytes}))
resource.setrlimit(resource.RLIMIT_NOFILE, ({open_files}, {open_files}))

sys.argv = ["{program}"]
runpy.run_path("{program}", run_name="__main__")
"""


def _child_environment(workdir: Path) -> dict[str, str]:
    """An environment built from nothing.

    Allowlisting rather than deleting known secrets: a variable that is not
    listed here cannot reach the child, including ones added later.
    """
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }


def _read_capped(path: Path, limit: int) -> tuple[str, bool]:
    if not path.is_file():
        return "", False
    raw = path.read_bytes()
    text = raw.decode("utf-8", "replace")
    if len(text) <= limit:
        return text, False
    return text[:limit] + f"\n... output cut off after {limit} characters ...", True


def run_python(
    code: str,
    *,
    limits: SandboxLimits | None = None,
    input_files: dict[str, bytes] | None = None,
) -> RunResult:
    """Run ``code`` as a Python program under :class:`SandboxLimits`.

    Args:
        code: The program. Written to ``main.py`` in a fresh directory.
        limits: Ceilings for the run.
        input_files: ``{name: contents}`` copied into the working directory
            before the run. Pass copies of project files here -- the sandbox
            never touches the originals.

    Raises:
        SandboxError: If the platform cannot enforce limits, the code is empty
            or oversized, or an input file name is unusable.
    """
    if sys.platform == "win32":  # pragma: no cover - not the target platform
        raise SandboxError(
            "running code is only supported where POSIX resource limits exist "
            "(Linux and macOS). Without them there is nothing holding a runaway "
            "program back, and pretending otherwise would be worse than "
            "refusing."
        )

    if not isinstance(code, str) or not code.strip():
        raise SandboxError("there is no code to run")
    if len(code) > MAX_CODE_CHARS:
        raise SandboxError(
            f"the program is {len(code)} characters, the limit is {MAX_CODE_CHARS}"
        )

    limits = limits or SandboxLimits()
    limits.validate()

    workdir = Path(tempfile.mkdtemp(prefix="caracat-run-"))
    try:
        original_digests: dict[str, str] = {}
        for name, contents in (input_files or {}).items():
            if Path(name).name.startswith(RESERVED_PREFIX):
                raise SandboxError(
                    f"input file name {name!r} uses the reserved "
                    f"{RESERVED_PREFIX!r} prefix, which belongs to the sandbox"
                )
            target = (workdir / name).resolve()
            if workdir not in target.parents:
                raise SandboxError(
                    f"input file name escapes the run directory: {name!r}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
            original_digests[target.relative_to(workdir).as_posix()] = hashlib.sha256(
                contents
            ).hexdigest()

        (workdir / f"{RESERVED_PREFIX}main.py").write_text(code, encoding="utf-8")
        (workdir / f"{RESERVED_PREFIX}runner.py").write_text(
            RUNNER_SOURCE.format(
                program=f"{RESERVED_PREFIX}main.py",
                memory_bytes=limits.memory_mb * 1024 * 1024,
                cpu_seconds=max(2, int(limits.timeout_seconds) + 1),
                file_bytes=limits.max_file_mb * 1024 * 1024,
                open_files=limits.max_open_files,
            ),
            encoding="utf-8",
        )

        stdout_path = workdir / f"{RESERVED_PREFIX}stdout.txt"
        stderr_path = workdir / f"{RESERVED_PREFIX}stderr.txt"
        started = time.monotonic()
        timed_out = False
        exit_code: int | None = None

        # Output goes to files rather than pipes so the file-size limit caps it.
        # A program printing without end would otherwise fill the server's
        # memory long before the timeout fires.
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            process = subprocess.Popen(  # fixed argv, never a shell
                [sys.executable, "-I", f"{RESERVED_PREFIX}runner.py"],
                cwd=workdir,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env=_child_environment(workdir),
                start_new_session=True,  # its own process group, so children die too
            )
            try:
                exit_code = process.wait(timeout=limits.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_group(process)
                exit_code = None

        duration = time.monotonic() - started
        stdout, cut_out = _read_capped(stdout_path, limits.max_output_chars)
        stderr, cut_err = _read_capped(stderr_path, limits.max_output_chars)

        produced = tuple(sorted(_changed_files(workdir, original_digests)))

        if timed_out:
            stderr += (
                f"\n[the program was stopped after {limits.timeout_seconds:g} seconds]"
            )

        return RunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=round(duration, 3),
            timed_out=timed_out,
            output_truncated=cut_out or cut_err,
            produced_files=produced,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _changed_files(workdir: Path, original_digests: dict[str, str]) -> list[str]:
    """Files worth fetching back: new ones, and inputs the program rewrote.

    An input file the program merely read is not interesting, and listing it
    would bury the one file the run actually produced.
    """
    changed: list[str] = []
    for item in workdir.rglob("*"):
        if not item.is_file() or item.name.startswith(RESERVED_PREFIX):
            continue
        name = item.relative_to(workdir).as_posix()
        before = original_digests.get(name)
        if before is None:
            changed.append(name)
            continue
        try:
            if hashlib.sha256(item.read_bytes()).hexdigest() != before:
                changed.append(name)
        except OSError:  # pragma: no cover - vanished mid-run
            continue
    return changed


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the process and anything it started."""
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):  # pragma: no cover - race
        process.kill()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)
