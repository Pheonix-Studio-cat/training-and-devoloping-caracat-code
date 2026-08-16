"""Tests for loading and validating training configurations."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from caracat_code.config import (
    ConfigError,
    load_training_config,
    parse_training_config,
)
from caracat_code.datasets import DatasetLicenseError

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_training.yaml"


def minimal_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "run_name": "test-run",
        "output_dir": "outputs/test-run",
        "hyperparameters": {
            "learning_rate": 1e-5,
            "epochs": 1,
            "batch_size": 2,
        },
    }
    config.update(overrides)
    return config


def test_shipped_example_config_is_valid() -> None:
    config = load_training_config(EXAMPLE_CONFIG)

    assert config.run_name == "caracat-code-example"
    assert config.model.base_model == "Qwen/Qwen3-Coder-Next"
    assert config.datasets == ()
    assert config.source_path == EXAMPLE_CONFIG


def test_defaults_are_applied() -> None:
    config = parse_training_config(minimal_config())

    assert config.model.base_model == "Qwen/Qwen3-Coder-Next"
    assert config.model.trust_remote_code is False
    assert config.seed == 42
    assert config.commercial_use_intended is False
    assert config.allow_personal_data is False
    assert config.hyperparameters.gradient_accumulation_steps == 1


@pytest.mark.parametrize("key", ["run_name", "output_dir", "hyperparameters"])
def test_missing_top_level_key_is_rejected(key: str) -> None:
    config = minimal_config()
    del config[key]

    with pytest.raises(ConfigError, match=key):
        parse_training_config(config)


@pytest.mark.parametrize("key", ["learning_rate", "epochs", "batch_size"])
def test_missing_hyperparameter_is_rejected(key: str) -> None:
    config = minimal_config()
    del config["hyperparameters"][key]  # type: ignore[index]

    with pytest.raises(ConfigError, match=key):
        parse_training_config(config)


def test_boolean_is_not_accepted_as_an_integer() -> None:
    config = minimal_config()
    config["hyperparameters"]["epochs"] = True  # type: ignore[index]

    with pytest.raises(ConfigError, match="must be an integer"):
        parse_training_config(config)


def test_non_positive_epochs_is_rejected() -> None:
    config = minimal_config()
    config["hyperparameters"]["epochs"] = 0  # type: ignore[index]

    with pytest.raises(ConfigError, match="must be >= 1"):
        parse_training_config(config)


def test_datasets_must_be_a_list() -> None:
    with pytest.raises(ConfigError, match="'datasets' must be a list"):
        parse_training_config(minimal_config(datasets={"name": "oops"}))


def test_dataset_license_gate_runs_during_config_parsing() -> None:
    config = minimal_config(
        datasets=[
            {
                "name": "mystery-corpus",
                "source": "https://example.org/data",
                "license": "unknown",
                "commercial_use": True,
                "attribution_required": False,
            }
        ]
    )

    with pytest.raises(DatasetLicenseError, match="not been established"):
        parse_training_config(config)


def test_commercial_intent_is_checked_against_declared_datasets() -> None:
    dataset = {
        "name": "nc-corpus",
        "source": "https://example.org/data",
        "license": "CC-BY-NC-4.0",
        "commercial_use": False,
        "attribution_required": False,
    }

    parse_training_config(minimal_config(datasets=[dataset]))

    with pytest.raises(DatasetLicenseError, match="commercial use is intended"):
        parse_training_config(
            minimal_config(datasets=[dataset], commercial_use_intended=True)
        )


def test_missing_file_is_reported_clearly(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="configuration file not found"):
        load_training_config(tmp_path / "nope.yaml")


def test_empty_file_is_reported_clearly(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ConfigError, match="empty"):
        load_training_config(path)


def test_malformed_yaml_is_reported_clearly(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("run_name: [unclosed\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="could not parse"):
        load_training_config(path)


def test_error_messages_include_the_file_path(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    config = minimal_config()
    del config["run_name"]
    path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ConfigError, match=r"invalid\.yaml"):
        load_training_config(path)


def test_summary_lists_declared_datasets() -> None:
    config = parse_training_config(
        minimal_config(
            datasets=[
                {
                    "name": "example-corpus",
                    "source": "https://example.org/data",
                    "license": "MIT",
                    "commercial_use": True,
                    "attribution_required": False,
                }
            ]
        )
    )

    summary = config.summary()

    assert "example-corpus" in summary
    assert "MIT" in summary
    assert "Qwen/Qwen3-Coder-Next" in summary
