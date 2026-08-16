"""Caracat Code -- tooling for an AI coding model based on Qwen3-Coder-Next.

Caracat Code is based on Qwen3-Coder-Next by Qwen. See the NOTICE file for
attribution and THIRD_PARTY_LICENSES.md for third-party components.
"""

from caracat_code.config import (
    ConfigError,
    ModelConfig,
    TrainingConfig,
    TrainingHyperparameters,
    load_training_config,
    parse_training_config,
)
from caracat_code.datasets import (
    DatasetLicenseError,
    DatasetSpec,
    check_dataset_licenses,
    parse_dataset_spec,
)
from caracat_code.evaluation import (
    EnvironmentInfo,
    EvaluationRun,
    GenerationSettings,
    collect_environment,
    write_report,
)
from caracat_code.interface import (
    ChatRequestError,
    InterfaceConfig,
    InterfaceConfigError,
    build_chat_payload,
    resolve_config,
)

__version__ = "0.1.0"

BASE_MODEL = "Qwen/Qwen3-Coder-Next"
"""The upstream model Caracat Code is derived from."""

__all__ = [
    "BASE_MODEL",
    "ChatRequestError",
    "ConfigError",
    "DatasetLicenseError",
    "DatasetSpec",
    "EnvironmentInfo",
    "EvaluationRun",
    "GenerationSettings",
    "InterfaceConfig",
    "InterfaceConfigError",
    "ModelConfig",
    "TrainingConfig",
    "TrainingHyperparameters",
    "__version__",
    "build_chat_payload",
    "check_dataset_licenses",
    "collect_environment",
    "load_training_config",
    "parse_dataset_spec",
    "parse_training_config",
    "resolve_config",
    "write_report",
]
