"""Tests for running code under limits.

The limits are the point, so most of these are attempts to break out of them:
never ending, allocating without bound, printing without bound, spawning
children, and reading the parent's secrets.
"""

from __future__ import annotations

import pytest

from caracat_code.sandbox import (
    RESERVED_PREFIX,
    RunResult,
    SandboxError,
    SandboxLimits,
    run_python,
)

FAST = SandboxLimits(timeout_seconds=5.0, memory_mb=256)


def run(code: str, **kwargs: object) -> RunResult:
    kwargs.setdefault("limits", FAST)
    return run_python(code, **kwargs)  # type: ignore[arg-type]


# ---- the ordinary case -------------------------------------------------


def test_a_program_runs_and_reports_its_output() -> None:
    result = run("print('hello from the sandbox')")

    assert result.succeeded
    assert result.exit_code == 0
    assert "hello from the sandbox" in result.stdout
    assert result.stderr == ""
    assert result.duration_seconds >= 0


def test_a_failing_program_reports_the_traceback() -> None:
    result = run("raise ValueError('boom')")

    assert not result.succeeded
    assert result.exit_code != 0
    assert "ValueError: boom" in result.stderr


def test_the_standard_library_is_available() -> None:
    result = run("import json; print(json.dumps({'ok': True}))")

    assert '{"ok": true}' in result.stdout


def test_files_the_program_writes_are_reported() -> None:
    result = run("open('report.csv', 'w').write('a,b\\n1,2\\n')")

    assert "report.csv" in result.produced_files


def test_the_sandbox_own_files_are_not_reported_as_output() -> None:
    result = run("print('nothing written')")

    assert result.produced_files == ()


# ---- input files -------------------------------------------------------


def test_input_files_are_placed_in_the_working_directory() -> None:
    result = run(
        "print(open('data.csv').read().strip())",
        input_files={"data.csv": b"name,value\nalpha,1"},
    )

    assert "alpha,1" in result.stdout


def test_an_input_file_may_sit_in_a_subdirectory() -> None:
    result = run(
        "print(open('sheets/data.csv').read().strip())",
        input_files={"sheets/data.csv": b"ok"},
    )

    assert "ok" in result.stdout


def test_an_input_name_cannot_escape_the_run_directory() -> None:
    with pytest.raises(SandboxError, match="escapes the run directory"):
        run("pass", input_files={"../escaped.txt": b"x"})


def test_the_original_is_untouched_because_only_bytes_are_passed() -> None:
    # The API takes contents, not paths, so there is no handle on the original
    # for the program to write through.
    result = run(
        "open('data.csv', 'w').write('destroyed')",
        input_files={"data.csv": b"original"},
    )

    assert result.succeeded


# ---- the limits --------------------------------------------------------


def test_a_program_that_never_ends_is_stopped() -> None:
    """Stopped, and said so.

    Which ceiling fires first is a race: a busy loop burns CPU as fast as the
    clock runs, so the wall-clock timeout and the CPU allowance finish neck and
    neck. The guarantee worth testing is the one the person sees -- the program
    is stopped, and the reason is stated rather than shown as a bare signal.
    """
    result = run("while True: pass", limits=SandboxLimits(timeout_seconds=2.0))

    assert result.stopped_by_limit
    assert not result.succeeded
    assert "the program was stopped" in result.stderr
    assert result.duration_seconds < 20


def test_a_run_killed_by_a_ceiling_explains_itself() -> None:
    """A memory kill must not surface as an unexplained negative exit code."""
    result = run(
        "x = bytearray(400 * 1024 * 1024)",
        limits=SandboxLimits(timeout_seconds=10.0, memory_mb=128),
    )

    assert not result.succeeded
    if result.exit_code is not None and result.exit_code < 0:
        assert result.stopped_by_limit
        assert "the program was stopped" in result.stderr


def test_a_normal_failure_is_not_reported_as_a_limit() -> None:
    result = run("raise SystemExit(3)")

    assert not result.stopped_by_limit
    assert result.exit_code == 3


def test_a_runaway_allocation_is_stopped() -> None:
    result = run(
        "x = bytearray(400 * 1024 * 1024)\nprint('allocated')",
        limits=SandboxLimits(timeout_seconds=10.0, memory_mb=128),
    )

    assert "allocated" not in result.stdout
    assert not result.succeeded


def test_endless_output_is_capped() -> None:
    result = run(
        "while True: print('x' * 1000)",
        limits=SandboxLimits(timeout_seconds=3.0, max_output_chars=500),
    )

    assert result.output_truncated
    assert "cut off after 500 characters" in result.stdout
    assert len(result.stdout) < 2000


def test_children_are_killed_with_the_parent() -> None:
    code = (
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "import time; time.sleep(60)\n"
    )

    result = run(code, limits=SandboxLimits(timeout_seconds=2.0))

    assert result.timed_out
    assert result.duration_seconds < 20


# ---- the environment ---------------------------------------------------


def test_the_api_key_is_not_visible_to_the_program(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CARACAT_API_KEY", "sk-should-never-be-visible")
    monkeypatch.setenv("HF_TOKEN", "hf-should-never-be-visible")

    result = run(
        "import os\nprint('CARACAT_API_KEY' in os.environ, 'HF_TOKEN' in os.environ)\n"
    )

    assert "False False" in result.stdout
    assert "should-never-be-visible" not in result.stdout


def test_the_environment_is_an_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("A_FUTURE_SECRET", "leaked")

    result = run("import os; print(sorted(os.environ))")

    assert "A_FUTURE_SECRET" not in result.stdout
    assert "PATH" in result.stdout


def test_each_run_gets_a_fresh_directory() -> None:
    run("open('left_behind.txt', 'w').write('x')")
    result = run("import os; print(os.listdir('.'))")

    assert "left_behind.txt" not in result.stdout


# ---- refusals ----------------------------------------------------------


@pytest.mark.parametrize("code", ["", "   ", "\n\n"])
def test_empty_code_is_refused(code: str) -> None:
    with pytest.raises(SandboxError, match="no code to run"):
        run(code)


def test_oversized_code_is_refused() -> None:
    with pytest.raises(SandboxError, match="the limit is"):
        run("print(1)\n" * 40_000)


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        (SandboxLimits(timeout_seconds=0), "timeout"),
        (SandboxLimits(timeout_seconds=1000), "timeout"),
        (SandboxLimits(memory_mb=1), "memory"),
        (SandboxLimits(max_output_chars=0), "output"),
    ],
)
def test_impossible_limits_are_refused(limits: SandboxLimits, message: str) -> None:
    with pytest.raises(SandboxError, match=message):
        run_python("print(1)", limits=limits)


# ---- name collisions ---------------------------------------------------


def test_a_project_file_named_main_py_is_not_overwritten() -> None:
    """The sandbox writes the program under a reserved prefix, precisely so a
    file called main.py -- a very common name -- survives being copied in."""
    result = run(
        "print(open('main.py').read().strip())",
        input_files={"main.py": b"# the user's own main.py"},
    )

    assert "the user's own main.py" in result.stdout


def test_an_input_file_cannot_claim_the_reserved_prefix() -> None:
    with pytest.raises(SandboxError, match="reserved"):
        run("pass", input_files={f"{RESERVED_PREFIX}runner.py": b"x"})


def test_sandbox_files_are_not_reported_as_produced() -> None:
    result = run("open('mine.txt', 'w').write('x')")

    assert result.produced_files == ("mine.txt",)


def test_an_input_the_program_only_read_is_not_listed() -> None:
    result = run(
        "print(open('data.csv').read())", input_files={"data.csv": b"a,b\n1,2\n"}
    )

    assert result.produced_files == ()


def test_an_input_the_program_rewrote_is_listed() -> None:
    result = run(
        "open('sheet.csv', 'w').write('changed\\n')",
        input_files={"sheet.csv": b"original\n"},
    )

    assert result.produced_files == ("sheet.csv",)
