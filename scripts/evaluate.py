#!/usr/bin/env python3
"""Record a Caracat Code evaluation run as a reproducible JSON report.

The point of this script is the record, not the number: a result is only worth
publishing when the conditions that produced it were captured alongside it.
Fields that are not supplied stay ``null`` and are listed in
``incomplete_fields`` -- they are never guessed.

Usage:
    python scripts/evaluate.py --dry-run --output-dir eval_runs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running the script directly from a checkout, without installing.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from caracat_code.evaluation import (  # noqa: E402
    EvaluationRun,
    GenerationSettings,
    collect_environment,
    write_report,
)

RECORDED_PACKAGES = ("caracat-code", "PyYAML")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record an evaluation run of Caracat Code.",
    )
    parser.add_argument("--model-name", default="Caracat Code")
    parser.add_argument("--model-version", help="Version of the evaluated model.")
    parser.add_argument(
        "--base-model",
        default="Qwen/Qwen3-Coder-Next",
        help="Upstream model the evaluated model derives from.",
    )
    parser.add_argument(
        "--base-model-revision", help="Upstream revision or commit hash."
    )
    parser.add_argument(
        "--quantization",
        help="Quantization used, e.g. 'none', 'int8', 'q4_k_m'.",
    )
    parser.add_argument("--test-set", help="Name or path of the test set.")
    parser.add_argument("--test-set-size", type=int, help="Number of test items.")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--context-length", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--hardware",
        help="Hardware description, e.g. '1x NVIDIA A100 80GB'. Not auto-detected.",
    )
    parser.add_argument(
        "--results",
        type=Path,
        help="Path to a JSON file holding the measured results.",
    )
    parser.add_argument("--notes", help="Free-form notes about the run.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("eval_runs"),
        help="Directory the JSON report is written to (default: eval_runs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Record the run without results, to check that the metadata is "
            "complete before spending time on a real evaluation."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    results: dict[str, object] = {}
    if args.results is not None:
        if args.dry_run:
            print("--results and --dry-run are mutually exclusive.", file=sys.stderr)
            return 2
        try:
            results = json.loads(args.results.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not read results from {args.results}: {exc}", file=sys.stderr)
            return 2
        if not isinstance(results, dict):
            print(
                f"{args.results}: expected a JSON object of metric names to values.",
                file=sys.stderr,
            )
            return 2
    elif not args.dry_run:
        print(
            "No results given. Pass --results <file.json> with the measured "
            "values, or --dry-run to record the metadata only.",
            file=sys.stderr,
        )
        return 2

    run = EvaluationRun(
        model_name=args.model_name,
        model_version=args.model_version,
        base_model=args.base_model,
        base_model_revision=args.base_model_revision,
        quantization=args.quantization,
        test_set=args.test_set,
        test_set_size=args.test_set_size,
        generation=GenerationSettings(
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            max_new_tokens=args.max_new_tokens,
            context_length=args.context_length,
            seed=args.seed,
        ),
        environment=collect_environment(
            hardware=args.hardware, packages=RECORDED_PACKAGES
        ),
        results=results,
        notes=args.notes,
        dry_run=args.dry_run,
    )

    report_path = write_report(run, args.output_dir)
    print(f"Report written to {report_path}")

    missing = run.incomplete_fields()
    if missing:
        print(
            "\nRecorded as null because they were not supplied: "
            f"{', '.join(missing)}.\n"
            "Results from a run with missing fields are not reproducible and "
            "must not be published as benchmark numbers.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
