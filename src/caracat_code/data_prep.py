"""Turning raw examples into a training dataset that is safe to train on.

Everything here runs *before* a training run, because the two mistakes this
module prevents cannot be undone afterwards:

- **Credentials in the training data.** A key that ends up in the weights cannot
  be removed from them. Rotating it is the only remedy, and you have to notice
  first. So a file containing something that looks like a credential is rejected
  outright, and the offending value is never printed back.
- **Data of unknown provenance.** Every dataset carries a :class:`DatasetSpec`
  through the same license gate the training configuration uses, so "we will sort
  the license out later" is not a reachable state.

Two input shapes are accepted per JSONL line::

    {"instruction": "...", "input": "...", "output": "..."}
    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}

Both are normalized to the message form on the way out.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from caracat_code.datasets import DatasetSpec, check_dataset_licenses
from caracat_code.interface import ALLOWED_ROLES

__all__ = [
    "DataPreparationError",
    "PreparationReport",
    "SecretFinding",
    "TrainingExample",
    "deduplicate",
    "load_examples",
    "normalize_example",
    "prepare_dataset",
    "scan_for_secrets",
    "split_examples",
]

MAX_FIELD_CHARS = 100_000
"""Upper bound per message. A longer one is far more likely a mistake than data."""

MIN_EXAMPLES_FOR_SPLIT = 2

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)"
            r"\s*[:=]\s*[\"']?([A-Za-z0-9/+_.-]{16,})"
        ),
    ),
)

PLACEHOLDER_MARKERS = (
    "your",
    "example",
    "placeholder",
    "changeme",
    "change-me",
    "dummy",
    "fake",
    "sample",
    "redacted",
    "xxxx",
    "....",
    "<",
)


class DataPreparationError(ValueError):
    """Raised when input data is malformed, unsafe or unusable."""


@dataclass(frozen=True)
class SecretFinding:
    """A possible credential, described without repeating its value."""

    line_number: int
    field: str
    pattern: str

    def describe(self) -> str:
        return f"line {self.line_number}, field {self.field!r}: {self.pattern}"


@dataclass(frozen=True)
class TrainingExample:
    """One normalized conversation."""

    messages: tuple[Mapping[str, str], ...]

    def fingerprint(self) -> str:
        """Stable identity of this example, used for deduplication."""
        payload = json.dumps(
            [dict(message) for message in self.messages],
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def character_count(self) -> int:
        return sum(len(message["content"]) for message in self.messages)

    def to_json_line(self) -> str:
        return json.dumps(
            {"messages": [dict(message) for message in self.messages]},
            ensure_ascii=False,
        )


@dataclass(frozen=True)
class PreparationReport:
    """What happened during preparation, for the manifest and the console."""

    input_path: str
    input_sha256: str
    lines_read: int
    examples_parsed: int
    duplicates_removed: int
    train_examples: int
    validation_examples: int
    validation_fraction: float
    seed: int
    dataset: DatasetSpec
    shortest_example_chars: int = 0
    longest_example_chars: int = 0
    mean_example_chars: float = 0.0
    output_files: tuple[str, ...] = field(default_factory=tuple)

    def to_manifest(self) -> dict[str, object]:
        manifest = asdict(self)
        manifest["dataset"] = asdict(self.dataset)
        manifest["output_files"] = list(self.output_files)
        return manifest


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def scan_for_secrets(
    text: str, *, line_number: int, field_name: str
) -> list[SecretFinding]:
    """Report anything in ``text`` that looks like a credential.

    Findings name the pattern, the line and the field -- never the matched value.
    Printing a suspected secret back into a terminal or a log would defeat the
    purpose of looking for it.
    """
    findings: list[SecretFinding] = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            captured = match.group(match.lastindex or 0)
            if _looks_like_placeholder(captured):
                continue
            findings.append(
                SecretFinding(line_number=line_number, field=field_name, pattern=name)
            )
            break  # one finding per pattern per field is enough to act on
    return findings


def _require_text(value: object, *, what: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataPreparationError(
            f"line {line_number}: {what} must be a non-empty string"
        )
    if len(value) > MAX_FIELD_CHARS:
        raise DataPreparationError(
            f"line {line_number}: {what} is {len(value)} characters, the limit is "
            f"{MAX_FIELD_CHARS}"
        )
    return value


def _messages_from_instruction_form(
    raw: Mapping[str, object], line_number: int
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    system = raw.get("system")
    if system is not None:
        messages.append(
            {
                "role": "system",
                "content": _require_text(
                    system, what="'system'", line_number=line_number
                ),
            }
        )

    instruction = _require_text(
        raw.get("instruction"), what="'instruction'", line_number=line_number
    )
    extra = raw.get("input")
    if extra is not None and not isinstance(extra, str):
        raise DataPreparationError(f"line {line_number}: 'input' must be a string")
    user_content = f"{instruction}\n\n{extra}" if (extra or "").strip() else instruction
    if len(user_content) > MAX_FIELD_CHARS:
        raise DataPreparationError(
            f"line {line_number}: instruction and input together are "
            f"{len(user_content)} characters, the limit is {MAX_FIELD_CHARS}"
        )

    messages.append({"role": "user", "content": user_content})
    messages.append(
        {
            "role": "assistant",
            "content": _require_text(
                raw.get("output"), what="'output'", line_number=line_number
            ),
        }
    )
    return messages


def _messages_from_chat_form(
    raw: Mapping[str, object], line_number: int
) -> list[dict[str, str]]:
    entries = raw.get("messages")
    if not isinstance(entries, list) or len(entries) < 2:
        raise DataPreparationError(
            f"line {line_number}: 'messages' must be a list of at least two entries"
        )

    messages: list[dict[str, str]] = []
    for position, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise DataPreparationError(
                f"line {line_number}: message {position} must be an object"
            )
        role = entry.get("role")
        if role not in ALLOWED_ROLES:
            raise DataPreparationError(
                f"line {line_number}: message {position} has role {role!r}; allowed "
                f"roles are {', '.join(sorted(ALLOWED_ROLES))}"
            )
        if role == "system" and position != 0:
            raise DataPreparationError(
                f"line {line_number}: a system message is only allowed as the first "
                f"entry, found one at position {position}"
            )
        content = _require_text(
            entry.get("content"),
            what=f"message {position} content",
            line_number=line_number,
        )
        messages.append({"role": role, "content": content})

    if messages[-1]["role"] != "assistant":
        raise DataPreparationError(
            f"line {line_number}: the last message must be the assistant's answer, "
            f"found {messages[-1]['role']!r}. Without it there is nothing to learn."
        )
    if not any(message["role"] == "user" for message in messages):
        raise DataPreparationError(
            f"line {line_number}: there is no user message in this example"
        )
    return messages


def normalize_example(
    raw: object, line_number: int
) -> tuple[TrainingExample, list[SecretFinding]]:
    """Normalize one raw record and scan it for credentials.

    Returns the example together with any findings, so the caller can collect
    every problem in the file and report them in one pass instead of stopping at
    the first.
    """
    if not isinstance(raw, Mapping):
        raise DataPreparationError(f"line {line_number}: expected a JSON object")

    if "messages" in raw:
        messages = _messages_from_chat_form(raw, line_number)
    elif "instruction" in raw:
        messages = _messages_from_instruction_form(raw, line_number)
    else:
        raise DataPreparationError(
            f"line {line_number}: expected either 'messages' or 'instruction'"
        )

    findings: list[SecretFinding] = []
    for position, message in enumerate(messages):
        findings.extend(
            scan_for_secrets(
                message["content"],
                line_number=line_number,
                field_name=f"{message['role']}[{position}]",
            )
        )

    return TrainingExample(messages=tuple(messages)), findings


def load_examples(path: str | Path) -> tuple[list[TrainingExample], int]:
    """Read a JSONL file, normalize every record and refuse any credential.

    Returns the examples and the number of lines read.

    Raises:
        DataPreparationError: If the file is missing, a record is malformed, or
            anything in it looks like a credential.
    """
    source = Path(path)
    if not source.is_file():
        raise DataPreparationError(f"input file not found: {source}")

    examples: list[TrainingExample] = []
    findings: list[SecretFinding] = []
    lines_read = 0

    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            lines_read += 1
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataPreparationError(
                    f"line {line_number}: not valid JSON: {exc.msg}"
                ) from exc
            example, line_findings = normalize_example(raw, line_number)
            examples.append(example)
            findings.extend(line_findings)

    if findings:
        listed = "\n".join(f"  - {finding.describe()}" for finding in findings)
        raise DataPreparationError(
            f"{len(findings)} possible credential(s) found in {source}:\n{listed}\n\n"
            "Nothing was written. Remove or replace these values before preparing "
            "the dataset. A credential that reaches the training data ends up in "
            "the weights, where it cannot be deleted -- if any of these are real, "
            "rotate them now.\n"
            "The matched values are deliberately not printed here."
        )

    if not examples:
        raise DataPreparationError(f"{source} contains no examples")

    return examples, lines_read


def deduplicate(
    examples: Iterable[TrainingExample],
) -> tuple[list[TrainingExample], int]:
    """Drop exact duplicates, keeping first occurrences. Returns kept and removed."""
    seen: set[str] = set()
    kept: list[TrainingExample] = []
    removed = 0
    for example in examples:
        fingerprint = example.fingerprint()
        if fingerprint in seen:
            removed += 1
            continue
        seen.add(fingerprint)
        kept.append(example)
    return kept, removed


def split_examples(
    examples: Sequence[TrainingExample],
    *,
    validation_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """Shuffle deterministically and split into training and validation sets.

    The split is seeded so that the same input produces the same split, which is
    what makes two runs comparable.
    """
    if not 0.0 <= validation_fraction < 1.0:
        raise DataPreparationError(
            f"validation fraction must be between 0 and 1 (exclusive), "
            f"got {validation_fraction}"
        )

    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)

    if validation_fraction == 0.0 or len(shuffled) < MIN_EXAMPLES_FOR_SPLIT:
        return shuffled, []

    validation_count = max(1, round(len(shuffled) * validation_fraction))
    validation_count = min(validation_count, len(shuffled) - 1)
    return shuffled[validation_count:], shuffled[:validation_count]


def _write_jsonl(path: Path, examples: Sequence[TrainingExample]) -> None:
    path.write_text(
        "".join(f"{example.to_json_line()}\n" for example in examples),
        encoding="utf-8",
    )


def prepare_dataset(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    dataset: DatasetSpec,
    validation_fraction: float = 0.1,
    seed: int = 42,
    commercial_use_intended: bool = False,
    allow_personal_data: bool = False,
) -> PreparationReport:
    """Prepare a training dataset and write it, with a manifest, to ``output_dir``.

    Raises:
        DataPreparationError: If the input is unusable or contains credentials.
        DatasetLicenseError: If the dataset's terms do not permit the intended use.
    """
    check_dataset_licenses(
        [dataset],
        commercial_use_intended=commercial_use_intended,
        allow_personal_data=allow_personal_data,
    )

    source = Path(input_path)
    examples, lines_read = load_examples(source)
    kept, duplicates_removed = deduplicate(examples)
    train, validation = split_examples(
        kept, validation_fraction=validation_fraction, seed=seed
    )

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    train_path = destination / "train.jsonl"
    validation_path = destination / "validation.jsonl"
    manifest_path = destination / "manifest.json"

    _write_jsonl(train_path, train)
    _write_jsonl(validation_path, validation)

    lengths = [example.character_count() for example in kept]
    report = PreparationReport(
        input_path=str(source),
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        lines_read=lines_read,
        examples_parsed=len(examples),
        duplicates_removed=duplicates_removed,
        train_examples=len(train),
        validation_examples=len(validation),
        validation_fraction=validation_fraction,
        seed=seed,
        dataset=dataset,
        shortest_example_chars=min(lengths),
        longest_example_chars=max(lengths),
        mean_example_chars=round(sum(lengths) / len(lengths), 1),
        output_files=(train_path.name, validation_path.name, manifest_path.name),
    )

    manifest_path.write_text(
        json.dumps(report.to_manifest(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
