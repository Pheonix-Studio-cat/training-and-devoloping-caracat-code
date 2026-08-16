"""Tests for the evaluation run recorder."""

from __future__ import annotations

import json
from pathlib import Path

from caracat_code.evaluation import (
    REPRODUCIBILITY_FIELDS,
    EvaluationRun,
    GenerationSettings,
    collect_environment,
    write_report,
)


def complete_run(**overrides: object) -> EvaluationRun:
    defaults: dict[str, object] = {
        "model_name": "Caracat Code",
        "model_version": "0.1.0",
        "base_model": "Qwen/Qwen3-Coder-Next",
        "base_model_revision": "abc123",
        "quantization": "none",
        "test_set": "internal-smoke-set",
        "test_set_size": 10,
        "generation": GenerationSettings(temperature=0.2, context_length=8192),
        "environment": collect_environment(hardware="1x NVIDIA A100 80GB"),
        "results": {"pass_rate": 0.5},
    }
    defaults.update(overrides)
    return EvaluationRun(**defaults)  # type: ignore[arg-type]


def test_a_fully_specified_run_has_no_incomplete_fields() -> None:
    assert complete_run().incomplete_fields() == ()


def test_unspecified_fields_are_reported_not_guessed() -> None:
    run = EvaluationRun(model_name="Caracat Code")

    missing = run.incomplete_fields()

    assert set(missing) == set(REPRODUCIBILITY_FIELDS)
    record = run.to_dict()
    assert record["model"]["version"] is None  # type: ignore[index]
    assert record["generation"]["temperature"] is None  # type: ignore[index]
    assert record["incomplete_fields"] == list(missing)


def test_quantization_none_string_counts_as_answered() -> None:
    assert "quantization" not in complete_run(quantization="none").incomplete_fields()
    assert "quantization" in complete_run(quantization=None).incomplete_fields()


def test_hardware_is_read_from_the_environment() -> None:
    run = complete_run(environment=collect_environment())

    assert "hardware" in run.incomplete_fields()


def test_hardware_is_never_auto_detected() -> None:
    assert collect_environment().hardware is None


def test_environment_records_python_and_platform() -> None:
    environment = collect_environment(packages=("pytest", "definitely-not-installed"))

    assert environment.python_version
    assert environment.platform
    assert "pytest" in environment.packages
    assert "definitely-not-installed" not in environment.packages


def test_record_always_contains_every_key() -> None:
    record = EvaluationRun(model_name="Caracat Code").to_dict()

    assert set(record) == {
        "run_id",
        "timestamp",
        "dry_run",
        "model",
        "test_set",
        "generation",
        "environment",
        "results",
        "notes",
        "incomplete_fields",
    }
    assert set(record["model"]) == {  # type: ignore[arg-type]
        "name",
        "version",
        "base_model",
        "base_model_revision",
        "quantization",
    }


def test_write_report_produces_readable_json(tmp_path: Path) -> None:
    run = complete_run()

    path = write_report(run, tmp_path)

    assert path.parent == tmp_path
    assert path.suffix == ".json"
    assert run.run_id in path.name

    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["model"]["base_model"] == "Qwen/Qwen3-Coder-Next"
    assert written["results"] == {"pass_rate": 0.5}
    assert written["incomplete_fields"] == []


def test_write_report_creates_the_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "eval_runs"

    path = write_report(complete_run(), target)

    assert path.is_file()


def test_reports_of_distinct_runs_do_not_collide(tmp_path: Path) -> None:
    first = write_report(complete_run(), tmp_path)
    second = write_report(complete_run(), tmp_path)

    assert first != second
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_stop_sequences_serialize_as_a_list(tmp_path: Path) -> None:
    run = complete_run(
        generation=GenerationSettings(
            temperature=0.0, context_length=4096, stop_sequences=("</s>",)
        )
    )

    written = json.loads(write_report(run, tmp_path).read_text(encoding="utf-8"))

    assert written["generation"]["stop_sequences"] == ["</s>"]
