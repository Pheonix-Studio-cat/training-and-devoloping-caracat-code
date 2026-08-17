"""Tests for dataset preparation, including the credential gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caracat_code.data_prep import (
    DataPreparationError,
    TrainingExample,
    deduplicate,
    load_examples,
    normalize_example,
    prepare_dataset,
    scan_for_secrets,
    split_examples,
)
from caracat_code.datasets import DatasetLicenseError, parse_dataset_spec

# Assembled at runtime so no credential-shaped literal sits in this file.
# None of these are real; they only have to match the shape of the real thing.
FAKE_OPENAI_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
FAKE_HF_TOKEN = "hf_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
FAKE_AWS_KEY = "AKIA" + "3QJ7ZK2WLPQD5RT9"

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DATASET = REPO_ROOT / "configs" / "example_dataset.jsonl"


def spec(**overrides: object):
    declaration: dict[str, object] = {
        "name": "test-set",
        "source": "hand-written",
        "license": "MIT",
        "commercial_use": True,
        "attribution_required": False,
    }
    declaration.update(overrides)
    return parse_dataset_spec(declaration)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def pair(question: str = "q", answer: str = "a") -> dict[str, object]:
    return {"instruction": question, "output": answer}


# ---- normalization ----------------------------------------------------


def test_instruction_form_becomes_messages() -> None:
    example, findings = normalize_example(pair("Add two numbers", "Use +"), 1)

    assert findings == []
    assert example.messages == (
        {"role": "user", "content": "Add two numbers"},
        {"role": "assistant", "content": "Use +"},
    )


def test_input_is_appended_to_the_instruction() -> None:
    example, _ = normalize_example(
        {"instruction": "Explain", "input": "x = 1", "output": "assignment"}, 1
    )

    assert example.messages[0]["content"] == "Explain\n\nx = 1"


def test_a_system_field_becomes_the_first_message() -> None:
    example, _ = normalize_example(
        {"system": "Be terse", "instruction": "Hi", "output": "Hello"}, 1
    )

    assert example.messages[0] == {"role": "system", "content": "Be terse"}


def test_chat_form_is_accepted() -> None:
    example, _ = normalize_example(
        {
            "messages": [
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"},
            ]
        },
        1,
    )

    assert len(example.messages) == 2


def test_both_forms_normalize_to_the_same_example() -> None:
    from_instruction, _ = normalize_example(pair("q", "a"), 1)
    from_chat, _ = normalize_example(
        {
            "messages": [
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"},
            ]
        },
        2,
    )

    assert from_instruction.fingerprint() == from_chat.fingerprint()


def test_a_record_without_a_known_shape_is_refused() -> None:
    with pytest.raises(DataPreparationError, match="'messages' or 'instruction'"):
        normalize_example({"prompt": "q", "completion": "a"}, 7)


def test_the_last_message_must_be_the_answer() -> None:
    with pytest.raises(DataPreparationError, match="must be the assistant's answer"):
        normalize_example(
            {
                "messages": [
                    {"role": "assistant", "content": "a"},
                    {"role": "user", "content": "q"},
                ]
            },
            1,
        )


def test_a_system_message_may_only_come_first() -> None:
    with pytest.raises(DataPreparationError, match="only allowed as the first"):
        normalize_example(
            {
                "messages": [
                    {"role": "user", "content": "q"},
                    {"role": "system", "content": "late"},
                    {"role": "assistant", "content": "a"},
                ]
            },
            1,
        )


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(DataPreparationError, match="allowed roles"):
        normalize_example(
            {
                "messages": [
                    {"role": "root", "content": "q"},
                    {"role": "assistant", "content": "a"},
                ]
            },
            1,
        )


def test_empty_content_is_refused() -> None:
    with pytest.raises(DataPreparationError, match="non-empty string"):
        normalize_example({"instruction": "  ", "output": "a"}, 1)


def test_error_messages_name_the_line() -> None:
    with pytest.raises(DataPreparationError, match="line 42"):
        normalize_example({"instruction": "q"}, 42)


# ---- credential scanning ----------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"key = {FAKE_OPENAI_KEY}", "OpenAI-style API key"),
        (f"token: {FAKE_HF_TOKEN}", "Hugging Face token"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private key block"),
        (FAKE_AWS_KEY, "AWS access key id"),
        ("password = h8Kd93jfKe83nfMs01x", "credential assignment"),
    ],
)
def test_credentials_are_detected(text: str, expected: str) -> None:
    findings = scan_for_secrets(text, line_number=3, field_name="assistant[1]")

    assert [finding.pattern for finding in findings] == [expected]
    assert findings[0].line_number == 3
    assert findings[0].field == "assistant[1]"


@pytest.mark.parametrize(
    "text",
    [
        "api_key = 'your-api-key-here'",
        "password = 'changeme-please-now'",
        "token = '<your-token-goes-here>'",
        "secret = 'example-value-not-real'",
        "just ordinary prose about passwords",
        "api_key = short",
        "AKIAIOSFODNN7EXAMPLE",
    ],
)
def test_placeholders_and_prose_are_not_flagged(text: str) -> None:
    assert scan_for_secrets(text, line_number=1, field_name="assistant[1]") == []


def test_a_finding_never_contains_the_value() -> None:
    findings = scan_for_secrets(
        f"use {FAKE_OPENAI_KEY}", line_number=1, field_name="assistant[1]"
    )

    assert FAKE_OPENAI_KEY not in findings[0].describe()
    assert FAKE_OPENAI_KEY not in repr(findings[0])


def test_a_file_with_a_credential_is_refused(tmp_path: Path) -> None:
    source = write_jsonl(
        tmp_path / "in.jsonl",
        [pair(), {"instruction": "auth?", "output": f"use {FAKE_OPENAI_KEY}"}],
    )

    with pytest.raises(DataPreparationError) as caught:
        load_examples(source)

    message = str(caught.value)
    assert "line 2" in message
    assert "OpenAI-style API key" in message
    assert "rotate them now" in message
    assert FAKE_OPENAI_KEY not in message


def test_every_credential_is_reported_in_one_pass(tmp_path: Path) -> None:
    source = write_jsonl(
        tmp_path / "in.jsonl",
        [
            {"instruction": "a", "output": f"use {FAKE_OPENAI_KEY}"},
            {"instruction": "b", "output": f"use {FAKE_HF_TOKEN}"},
        ],
    )

    with pytest.raises(DataPreparationError, match="2 possible credential"):
        load_examples(source)


def test_nothing_is_written_when_a_credential_is_found(tmp_path: Path) -> None:
    source = write_jsonl(
        tmp_path / "in.jsonl", [{"instruction": "a", "output": FAKE_OPENAI_KEY}]
    )
    output = tmp_path / "out"

    with pytest.raises(DataPreparationError):
        prepare_dataset(source, output, dataset=spec())

    assert not output.exists() or not list(output.iterdir())


# ---- loading, deduplication, splitting --------------------------------


def test_blank_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "in.jsonl"
    path.write_text(json.dumps(pair()) + "\n\n\n", encoding="utf-8")

    examples, lines_read = load_examples(path)

    assert len(examples) == 1
    assert lines_read == 1


def test_malformed_json_names_the_line(tmp_path: Path) -> None:
    path = tmp_path / "in.jsonl"
    path.write_text(json.dumps(pair()) + "\n{not json\n", encoding="utf-8")

    with pytest.raises(DataPreparationError, match="line 2: not valid JSON"):
        load_examples(path)


def test_a_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(DataPreparationError, match="input file not found"):
        load_examples(tmp_path / "nope.jsonl")


def test_an_empty_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "in.jsonl"
    path.write_text("\n\n", encoding="utf-8")

    with pytest.raises(DataPreparationError, match="no examples"):
        load_examples(path)


def test_duplicates_are_removed_keeping_the_first() -> None:
    first, _ = normalize_example(pair("q", "a"), 1)
    same, _ = normalize_example(pair("q", "a"), 2)
    other, _ = normalize_example(pair("x", "y"), 3)

    kept, removed = deduplicate([first, same, other])

    assert removed == 1
    assert [example.messages[0]["content"] for example in kept] == ["q", "x"]


def examples(count: int) -> list[TrainingExample]:
    return [normalize_example(pair(f"q{i}", f"a{i}"), i)[0] for i in range(count)]


def test_the_split_is_deterministic() -> None:
    first = split_examples(examples(20), seed=7)
    second = split_examples(examples(20), seed=7)

    assert [e.fingerprint() for e in first[0]] == [e.fingerprint() for e in second[0]]


def test_a_different_seed_gives_a_different_split() -> None:
    with_7 = split_examples(examples(20), seed=7)[1]
    with_8 = split_examples(examples(20), seed=8)[1]

    assert [e.fingerprint() for e in with_7] != [e.fingerprint() for e in with_8]


def test_the_split_keeps_every_example() -> None:
    train, validation = split_examples(examples(20), validation_fraction=0.25)

    assert len(train) == 15
    assert len(validation) == 5


def test_a_zero_fraction_produces_no_validation_set() -> None:
    train, validation = split_examples(examples(10), validation_fraction=0.0)

    assert len(train) == 10
    assert validation == []


def test_the_training_set_is_never_emptied() -> None:
    train, validation = split_examples(examples(2), validation_fraction=0.9)

    assert len(train) == 1
    assert len(validation) == 1


def test_a_single_example_cannot_be_split() -> None:
    train, validation = split_examples(examples(1), validation_fraction=0.5)

    assert len(train) == 1
    assert validation == []


@pytest.mark.parametrize("fraction", [-0.1, 1.0, 1.5])
def test_an_impossible_fraction_is_refused(fraction: float) -> None:
    with pytest.raises(DataPreparationError, match="between 0 and 1"):
        split_examples(examples(10), validation_fraction=fraction)


# ---- end to end -------------------------------------------------------


def test_prepare_writes_files_and_a_manifest(tmp_path: Path) -> None:
    source = write_jsonl(
        tmp_path / "in.jsonl",
        [pair(f"q{i}", f"a{i}") for i in range(10)] + [pair("q0", "a0")],
    )
    output = tmp_path / "out"

    report = prepare_dataset(source, output, dataset=spec(), validation_fraction=0.2)

    assert report.duplicates_removed == 1
    assert report.train_examples + report.validation_examples == 10
    assert (output / "train.jsonl").is_file()
    assert (output / "validation.jsonl").is_file()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset"]["license"] == "MIT"
    assert manifest["duplicates_removed"] == 1
    assert manifest["seed"] == 42
    assert len(manifest["input_sha256"]) == 64


def test_written_lines_are_valid_json_in_message_form(tmp_path: Path) -> None:
    source = write_jsonl(
        tmp_path / "in.jsonl", [pair(f"q{i}", f"a{i}") for i in range(5)]
    )
    output = tmp_path / "out"

    prepare_dataset(source, output, dataset=spec(), validation_fraction=0.0)

    for line in (output / "train.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        assert set(record) == {"messages"}
        assert record["messages"][-1]["role"] == "assistant"


def test_the_license_gate_applies_to_prepared_datasets(tmp_path: Path) -> None:
    source = write_jsonl(tmp_path / "in.jsonl", [pair()])

    with pytest.raises(DatasetLicenseError, match="commercial use is intended"):
        prepare_dataset(
            source,
            tmp_path / "out",
            dataset=spec(license="CC-BY-NC-4.0", commercial_use=False),
            commercial_use_intended=True,
        )


def test_personal_data_is_blocked_by_default(tmp_path: Path) -> None:
    source = write_jsonl(tmp_path / "in.jsonl", [pair()])

    with pytest.raises(DatasetLicenseError, match="personal data"):
        prepare_dataset(
            source, tmp_path / "out", dataset=spec(contains_personal_data=True)
        )


def test_the_shipped_example_dataset_prepares_cleanly(tmp_path: Path) -> None:
    report = prepare_dataset(EXAMPLE_DATASET, tmp_path / "out", dataset=spec())

    assert report.examples_parsed == 5
    assert report.duplicates_removed == 0
    assert report.train_examples + report.validation_examples == 5
