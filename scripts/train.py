#!/usr/bin/env python3
"""Entry point for Caracat Code training runs.

This script does not train yet. It loads a training configuration, validates
it, and enforces the dataset license gate -- so a configuration is proven sound
before any expensive run is wired up. Shipping an untested training loop would
be worse than shipping none.

Usage:
    python scripts/train.py --config configs/example_training.yaml --validate-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running the script directly from a checkout, without installing.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from caracat_code.config import ConfigError, load_training_config  # noqa: E402
from caracat_code.datasets import DatasetLicenseError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a Caracat Code training configuration.",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to a YAML training configuration.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Validate the configuration and exit successfully. Without this "
            "flag the script reports that training is not implemented yet."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_training_config(args.config)
    except DatasetLicenseError as exc:
        print(f"Dataset license check failed:\n  {exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"Invalid configuration:\n  {exc}", file=sys.stderr)
        return 2

    print("Configuration is valid.\n")
    print(config.summary())

    if config.datasets:
        attributions = [spec for spec in config.datasets if spec.attribution_required]
        if attributions:
            print("\nAttribution required for:")
            for spec in attributions:
                print(f"  - {spec.name}: {spec.attribution_text()}")

    if args.validate_only:
        return 0

    print(
        "\nTraining is not implemented yet.\n"
        "This repository currently contains the configuration, license and "
        "reproducibility tooling for Caracat Code. Adding a training loop "
        "requires training dependencies, and each one must first be recorded "
        "in THIRD_PARTY_LICENSES.md with its license read from the primary "
        "source (see CLAUDE.md).\n"
        "Re-run with --validate-only to check configurations in the meantime.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
