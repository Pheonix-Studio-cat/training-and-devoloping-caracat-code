"""End-to-end tests for the command-line entry points."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAIN = REPO_ROOT / "scripts" / "train.py"
EVALUATE = REPO_ROOT / "scripts" / "evaluate.py"
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_training.yaml"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def test_train_validates_the_example_config() -> None:
    result = run(TRAIN, "--config", str(EXAMPLE_CONFIG), "--validate-only")

    assert result.returncode == 0, result.stderr
    assert "Configuration is valid." in result.stdout
    assert "Qwen/Qwen3-Coder-Next" in result.stdout


def test_train_without_validate_only_reports_that_training_is_unimplemented() -> None:
    result = run(TRAIN, "--config", str(EXAMPLE_CONFIG))

    assert result.returncode == 1
    assert "Training is not implemented yet." in result.stderr


def test_train_rejects_an_unlicensed_dataset(tmp_path: Path) -> None:
    config = {
        "run_name": "bad-run",
        "output_dir": "outputs/bad-run",
        "hyperparameters": {"learning_rate": 1e-5, "epochs": 1, "batch_size": 1},
        "datasets": [
            {
                "name": "mystery-corpus",
                "source": "https://example.org/data",
                "license": "unknown",
                "commercial_use": True,
                "attribution_required": False,
            }
        ],
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")

    result = run(TRAIN, "--config", str(path), "--validate-only")

    assert result.returncode == 2
    assert "Dataset license check failed" in result.stderr
    assert "mystery-corpus" in result.stderr


def test_train_reports_a_missing_config_file(tmp_path: Path) -> None:
    result = run(TRAIN, "--config", str(tmp_path / "nope.yaml"), "--validate-only")

    assert result.returncode == 2
    assert "configuration file not found" in result.stderr


def test_evaluate_dry_run_writes_a_report(tmp_path: Path) -> None:
    result = run(EVALUATE, "--dry-run", "--output-dir", str(tmp_path))

    assert result.returncode == 0, result.stderr
    reports = list(tmp_path.glob("*.json"))
    assert len(reports) == 1

    record = json.loads(reports[0].read_text(encoding="utf-8"))
    assert record["dry_run"] is True
    assert record["model"]["base_model"] == "Qwen/Qwen3-Coder-Next"
    assert record["results"] == {}
    assert "test_set" in record["incomplete_fields"]
    assert "not reproducible" in result.stderr


def test_evaluate_requires_results_or_dry_run(tmp_path: Path) -> None:
    result = run(EVALUATE, "--output-dir", str(tmp_path))

    assert result.returncode == 2
    assert "No results given" in result.stderr
    assert list(tmp_path.glob("*.json")) == []


def test_evaluate_records_supplied_results(tmp_path: Path) -> None:
    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps({"pass_rate": 0.42}), encoding="utf-8")

    result = run(
        EVALUATE,
        "--results",
        str(results_file),
        "--output-dir",
        str(tmp_path),
        "--model-version",
        "0.1.0",
        "--base-model-revision",
        "abc123",
        "--quantization",
        "none",
        "--test-set",
        "internal-smoke-set",
        "--temperature",
        "0.2",
        "--context-length",
        "8192",
        "--hardware",
        "1x NVIDIA A100 80GB",
    )

    assert result.returncode == 0, result.stderr
    reports = [p for p in tmp_path.glob("*.json") if p != results_file]
    record = json.loads(reports[0].read_text(encoding="utf-8"))

    assert record["results"] == {"pass_rate": 0.42}
    assert record["incomplete_fields"] == []
    assert record["environment"]["hardware"] == "1x NVIDIA A100 80GB"


def test_evaluate_rejects_results_with_dry_run(tmp_path: Path) -> None:
    results_file = tmp_path / "results.json"
    results_file.write_text("{}", encoding="utf-8")

    result = run(
        EVALUATE,
        "--dry-run",
        "--results",
        str(results_file),
        "--output-dir",
        str(tmp_path),
    )

    assert result.returncode == 2
    assert "mutually exclusive" in result.stderr
