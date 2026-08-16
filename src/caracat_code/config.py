"""Training configuration: loading, parsing and validation.

A configuration is only accepted once it is complete and its datasets have
passed the license gate in :mod:`caracat_code.datasets`. Nothing is inferred
from a default where the answer has legal consequences.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from caracat_code.datasets import (
    DatasetLicenseError,
    DatasetSpec,
    check_dataset_licenses,
    parse_dataset_spec,
)

__all__ = [
    "ConfigError",
    "ModelConfig",
    "TrainingConfig",
    "TrainingHyperparameters",
    "load_training_config",
    "parse_training_config",
]

DEFAULT_BASE_MODEL = "Qwen/Qwen3-Coder-Next"


class ConfigError(ValueError):
    """Raised when a training configuration is missing or malformed."""


@dataclass(frozen=True)
class ModelConfig:
    """Which model is being fine-tuned, at which revision."""

    base_model: str = DEFAULT_BASE_MODEL
    revision: str | None = None
    quantization: str | None = None
    trust_remote_code: bool = False


@dataclass(frozen=True)
class TrainingHyperparameters:
    """Hyperparameters recorded with the run so results can be reproduced."""

    learning_rate: float
    epochs: int
    batch_size: int
    gradient_accumulation_steps: int = 1
    max_sequence_length: int | None = None
    warmup_ratio: float = 0.0
    weight_decay: float = 0.0


@dataclass(frozen=True)
class TrainingConfig:
    """A complete, validated training configuration."""

    run_name: str
    output_dir: str
    model: ModelConfig
    hyperparameters: TrainingHyperparameters
    datasets: tuple[DatasetSpec, ...] = ()
    seed: int = 42
    commercial_use_intended: bool = False
    allow_personal_data: bool = False
    notes: str | None = None
    source_path: Path | None = field(default=None, compare=False)

    def summary(self) -> str:
        """A short, human-readable description for logs and CLI output."""
        dataset_lines = [
            f"  - {spec.name} ({spec.license}, source: {spec.source})"
            for spec in self.datasets
        ] or ["  (none declared)"]
        return "\n".join(
            [
                f"run name        : {self.run_name}",
                f"base model      : {self.model.base_model}",
                f"revision        : {self.model.revision or '(default)'}",
                f"quantization    : {self.model.quantization or 'none'}",
                f"output dir      : {self.output_dir}",
                f"seed            : {self.seed}",
                f"commercial use  : {self.commercial_use_intended}",
                f"datasets ({len(self.datasets)}):",
                *dataset_lines,
            ]
        )


def _require_mapping(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{what} must be a mapping, got {type(value).__name__}")
    return value


def _require(raw: Mapping[str, object], key: str, what: str) -> object:
    if key not in raw:
        raise ConfigError(f"{what}: missing required key {key!r}")
    return raw[key]


def _as_str(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{what} must be a non-empty string, got {value!r}")
    return value.strip()


def _as_optional_str(value: object, what: str) -> str | None:
    if value is None:
        return None
    return _as_str(value, what)


def _as_int(value: object, what: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{what} must be an integer, got {value!r}")
    if minimum is not None and value < minimum:
        raise ConfigError(f"{what} must be >= {minimum}, got {value}")
    return value


def _as_float(value: object, what: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{what} must be a number, got {value!r}")
    number = float(value)
    if minimum is not None and number < minimum:
        raise ConfigError(f"{what} must be >= {minimum}, got {number}")
    return number


def _as_bool(value: object, what: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ConfigError(f"{what} must be true or false, got {value!r}")
    return value


def _parse_model(raw: object) -> ModelConfig:
    if raw is None:
        return ModelConfig()
    mapping = _require_mapping(raw, "'model'")
    return ModelConfig(
        base_model=_as_str(
            mapping.get("base_model", DEFAULT_BASE_MODEL), "model.base_model"
        ),
        revision=_as_optional_str(mapping.get("revision"), "model.revision"),
        quantization=_as_optional_str(
            mapping.get("quantization"), "model.quantization"
        ),
        trust_remote_code=_as_bool(
            mapping.get("trust_remote_code"), "model.trust_remote_code", default=False
        ),
    )


def _parse_hyperparameters(raw: object) -> TrainingHyperparameters:
    mapping = _require_mapping(raw, "'hyperparameters'")
    what = "hyperparameters"
    max_sequence_length = mapping.get("max_sequence_length")
    return TrainingHyperparameters(
        learning_rate=_as_float(
            _require(mapping, "learning_rate", what),
            f"{what}.learning_rate",
            minimum=0.0,
        ),
        epochs=_as_int(_require(mapping, "epochs", what), f"{what}.epochs", minimum=1),
        batch_size=_as_int(
            _require(mapping, "batch_size", what), f"{what}.batch_size", minimum=1
        ),
        gradient_accumulation_steps=_as_int(
            mapping.get("gradient_accumulation_steps", 1),
            f"{what}.gradient_accumulation_steps",
            minimum=1,
        ),
        max_sequence_length=(
            None
            if max_sequence_length is None
            else _as_int(max_sequence_length, f"{what}.max_sequence_length", minimum=1)
        ),
        warmup_ratio=_as_float(
            mapping.get("warmup_ratio", 0.0), f"{what}.warmup_ratio", minimum=0.0
        ),
        weight_decay=_as_float(
            mapping.get("weight_decay", 0.0), f"{what}.weight_decay", minimum=0.0
        ),
    )


def parse_training_config(
    raw: object, *, source_path: Path | None = None
) -> TrainingConfig:
    """Validate a configuration mapping and return a :class:`TrainingConfig`.

    Raises:
        ConfigError: If the configuration is structurally invalid.
        DatasetLicenseError: If a declared dataset fails the license gate.
    """
    mapping = _require_mapping(raw, "the training configuration")

    raw_datasets = mapping.get("datasets", [])
    if raw_datasets is None:
        raw_datasets = []
    if not isinstance(raw_datasets, list):
        raise ConfigError(
            f"'datasets' must be a list, got {type(raw_datasets).__name__}"
        )

    datasets = tuple(
        parse_dataset_spec(entry, index)  # type: ignore[arg-type]
        for index, entry in enumerate(raw_datasets)
    )

    commercial_use_intended = _as_bool(
        mapping.get("commercial_use_intended"),
        "'commercial_use_intended'",
        default=False,
    )
    allow_personal_data = _as_bool(
        mapping.get("allow_personal_data"), "'allow_personal_data'", default=False
    )

    check_dataset_licenses(
        datasets,
        commercial_use_intended=commercial_use_intended,
        allow_personal_data=allow_personal_data,
    )

    return TrainingConfig(
        run_name=_as_str(
            _require(mapping, "run_name", "the training configuration"), "'run_name'"
        ),
        output_dir=_as_str(
            _require(mapping, "output_dir", "the training configuration"),
            "'output_dir'",
        ),
        model=_parse_model(mapping.get("model")),
        hyperparameters=_parse_hyperparameters(
            _require(mapping, "hyperparameters", "the training configuration")
        ),
        datasets=datasets,
        seed=_as_int(mapping.get("seed", 42), "'seed'"),
        commercial_use_intended=commercial_use_intended,
        allow_personal_data=allow_personal_data,
        notes=_as_optional_str(mapping.get("notes"), "'notes'"),
        source_path=source_path,
    )


def load_training_config(path: str | Path) -> TrainingConfig:
    """Load and validate a YAML training configuration from ``path``.

    Raises:
        ConfigError: If the file is missing, unparseable or invalid.
        DatasetLicenseError: If a declared dataset fails the license gate.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"configuration file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse {config_path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"configuration file is empty: {config_path}")

    try:
        return parse_training_config(raw, source_path=config_path)
    except DatasetLicenseError as exc:
        raise DatasetLicenseError(f"{config_path}: {exc}") from exc
    except ConfigError as exc:
        raise ConfigError(f"{config_path}: {exc}") from exc
