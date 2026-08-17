#!/usr/bin/env python3
"""Prepare a training dataset from raw examples.

Reads a JSONL file, checks the structure, refuses anything that looks like a
credential, removes exact duplicates, splits off a validation set and writes a
manifest recording what was produced and under which license.

    python scripts/prepare_dataset.py \\
        --input my_examples.jsonl \\
        --output-dir data/run-01 \\
        --name my-examples \\
        --source "hand-written, own work" \\
        --license Apache-2.0 \\
        --commercial-use yes \\
        --attribution-required no

The license questions have no defaults on purpose. An unanswered licensing
question is not the same as "no", and the project does not treat it as one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running the script directly from a checkout, without installing.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from caracat_code.data_prep import (  # noqa: E402
    DataPreparationError,
    prepare_dataset,
)
from caracat_code.datasets import (  # noqa: E402
    DatasetLicenseError,
    parse_dataset_spec,
)

YES_NO = ("yes", "no")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate a training dataset.",
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="JSONL file with raw examples."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for train.jsonl, validation.jsonl and manifest.json.",
    )

    licensing = parser.add_argument_group("dataset provenance (all required)")
    licensing.add_argument("--name", required=True, help="Short dataset name.")
    licensing.add_argument("--source", required=True, help="Where the data came from.")
    licensing.add_argument(
        "--license",
        required=True,
        help="License identifier. 'unknown' is rejected -- establish it first.",
    )
    licensing.add_argument(
        "--commercial-use",
        required=True,
        choices=YES_NO,
        help="Does the license permit commercial use?",
    )
    licensing.add_argument(
        "--attribution-required",
        required=True,
        choices=YES_NO,
        help="Does the license require attribution?",
    )
    licensing.add_argument(
        "--attribution",
        help="Attribution text to reproduce. Required when --attribution-required yes.",
    )
    licensing.add_argument(
        "--personal-data",
        choices=YES_NO,
        help="Does the data contain personal information?",
    )
    licensing.add_argument("--notes", help="Free-form notes about the dataset.")

    intent = parser.add_argument_group("intended use")
    intent.add_argument(
        "--commercial-use-intended",
        action="store_true",
        help="Fail unless the dataset permits commercial use.",
    )
    intent.add_argument(
        "--allow-personal-data",
        action="store_true",
        help="Permit a dataset flagged as containing personal data.",
    )

    split = parser.add_argument_group("split")
    split.add_argument(
        "--validation-fraction",
        type=float,
        default=0.1,
        help="Share held back for validation (default: 0.1).",
    )
    split.add_argument(
        "--seed", type=int, default=42, help="Shuffle seed (default: 42)."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    declaration: dict[str, object] = {
        "name": args.name,
        "source": args.source,
        "license": args.license,
        "commercial_use": args.commercial_use == "yes",
        "attribution_required": args.attribution_required == "yes",
    }
    if args.attribution is not None:
        declaration["attribution"] = args.attribution
    if args.personal_data is not None:
        declaration["contains_personal_data"] = args.personal_data == "yes"
    if args.notes is not None:
        declaration["notes"] = args.notes

    try:
        dataset = parse_dataset_spec(declaration)
    except DatasetLicenseError as exc:
        print(f"Dataset declaration rejected:\n  {exc}", file=sys.stderr)
        return 2

    try:
        report = prepare_dataset(
            args.input,
            args.output_dir,
            dataset=dataset,
            validation_fraction=args.validation_fraction,
            seed=args.seed,
            commercial_use_intended=args.commercial_use_intended,
            allow_personal_data=args.allow_personal_data,
        )
    except DatasetLicenseError as exc:
        print(f"Dataset license check failed:\n  {exc}", file=sys.stderr)
        return 2
    except DataPreparationError as exc:
        print(f"Dataset not prepared:\n\n{exc}", file=sys.stderr)
        return 2

    print(f"Prepared {report.train_examples + report.validation_examples} examples.\n")
    print(f"  read from          : {report.input_path}")
    print(f"  lines read         : {report.lines_read}")
    print(f"  duplicates removed : {report.duplicates_removed}")
    print(f"  training set       : {report.train_examples}")
    print(f"  validation set     : {report.validation_examples}")
    print(
        f"  example size       : {report.shortest_example_chars} to "
        f"{report.longest_example_chars} chars "
        f"(mean {report.mean_example_chars})"
    )
    print(f"  license            : {dataset.license}")
    print(f"\nWritten to {Path(args.output_dir).resolve()}")

    if dataset.attribution_required:
        print(f"\nAttribution to reproduce: {dataset.attribution_text()}")
    if report.validation_examples == 0:
        print(
            "\nNo validation set was created -- there are too few examples, or the "
            "fraction was set to 0. Without one there is no way to tell whether "
            "the model learned or merely memorized.",
            file=sys.stderr,
        )

    print(
        "\nRecord this dataset in THIRD_PARTY_LICENSES.md if it is not your own "
        "work, and fill in the data section of docs/FINETUNING.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
