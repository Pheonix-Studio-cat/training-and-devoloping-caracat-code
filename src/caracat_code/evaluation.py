"""Reproducible recording of evaluation runs.

A benchmark number without its context is not a result, it is a rumour. This
module fixes the shape of an evaluation record so that every run carries the
information needed to reproduce it: model version, base model version,
quantization, hardware, software versions, test set, generation settings,
context length and results.

Fields that cannot be determined are recorded as ``null`` and listed in
``incomplete_fields``. Nothing is guessed to make a report look complete.
"""

from __future__ import annotations

import json
import platform
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "EnvironmentInfo",
    "EvaluationRun",
    "GenerationSettings",
    "collect_environment",
    "write_report",
]

REPRODUCIBILITY_FIELDS: tuple[str, ...] = (
    "model_version",
    "base_model",
    "base_model_revision",
    "quantization",
    "test_set",
    "hardware",
    "context_length",
    "temperature",
)
"""Fields whose absence makes a result impossible to reproduce."""


@dataclass(frozen=True)
class GenerationSettings:
    """Decoding parameters used for the run."""

    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_new_tokens: int | None = None
    context_length: int | None = None
    seed: int | None = None
    stop_sequences: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnvironmentInfo:
    """Software and hardware context of the run."""

    python_version: str
    platform: str
    processor: str | None = None
    hardware: str | None = None
    packages: Mapping[str, str] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    """A single evaluation run and everything needed to repeat it."""

    model_name: str
    model_version: str | None = None
    base_model: str | None = None
    base_model_revision: str | None = None
    quantization: str | None = None
    test_set: str | None = None
    test_set_size: int | None = None
    generation: GenerationSettings = field(default_factory=GenerationSettings)
    environment: EnvironmentInfo | None = None
    results: Mapping[str, object] = field(default_factory=dict)
    notes: str | None = None
    dry_run: bool = False
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def incomplete_fields(self) -> tuple[str, ...]:
        """Reproducibility fields that were not recorded for this run.

        ``quantization`` counts as recorded when it is explicitly the string
        ``"none"``; ``None`` means the question was never answered.
        """
        missing = []
        for name in REPRODUCIBILITY_FIELDS:
            if name in {"context_length", "temperature"}:
                value = getattr(self.generation, name)
            elif name == "hardware":
                value = self.environment.hardware if self.environment else None
            else:
                value = getattr(self, name)
            if value is None:
                missing.append(name)
        return tuple(missing)

    def to_dict(self) -> dict[str, object]:
        """The full record, with every key present even when its value is null."""
        environment = asdict(self.environment) if self.environment is not None else None
        if environment is not None:
            environment["packages"] = dict(environment["packages"])

        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "model": {
                "name": self.model_name,
                "version": self.model_version,
                "base_model": self.base_model,
                "base_model_revision": self.base_model_revision,
                "quantization": self.quantization,
            },
            "test_set": {
                "name": self.test_set,
                "size": self.test_set_size,
            },
            "generation": {
                **asdict(self.generation),
                "stop_sequences": list(self.generation.stop_sequences),
            },
            "environment": environment,
            "results": dict(self.results),
            "notes": self.notes,
            "incomplete_fields": list(self.incomplete_fields()),
        }


def collect_environment(
    *,
    hardware: str | None = None,
    packages: Sequence[str] = (),
) -> EnvironmentInfo:
    """Capture the software environment, and the hardware if it was supplied.

    Hardware is not auto-detected: an accelerator label guessed from the host
    would be worse than an honest ``null``. Pass ``hardware`` explicitly, e.g.
    ``"1x NVIDIA A100 80GB"``.

    Args:
        hardware: Free-form description of the hardware used.
        packages: Distribution names whose installed versions should be
            recorded. Packages that are not installed are skipped.
    """
    versions: dict[str, str] = {}
    if packages:
        from importlib.metadata import PackageNotFoundError, version

        for name in packages:
            try:
                versions[name] = version(name)
            except PackageNotFoundError:
                continue

    return EnvironmentInfo(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        processor=platform.processor() or None,
        hardware=hardware,
        packages=versions,
    )


def write_report(run: EvaluationRun, output_dir: str | Path) -> Path:
    """Write ``run`` as JSON into ``output_dir`` and return the file path.

    The file is named ``<timestamp>-<run_id>.json`` so runs sort chronologically
    and never overwrite one another.
    """
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    stamp = run.timestamp.replace(":", "").replace("-", "")
    report_path = directory / f"{stamp}-{run.run_id}.json"
    report_path.write_text(
        json.dumps(run.to_dict(), indent=2, sort_keys=False, default=str) + "\n",
        encoding="utf-8",
    )
    return report_path
