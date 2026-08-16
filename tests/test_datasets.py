"""Tests for the dataset license gate."""

from __future__ import annotations

import pytest

from caracat_code.datasets import (
    DatasetLicenseError,
    DatasetSpec,
    check_dataset_licenses,
    parse_dataset_spec,
)


def valid_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "name": "example-corpus",
        "source": "https://example.org/data",
        "license": "MIT",
        "commercial_use": True,
        "attribution_required": False,
    }
    entry.update(overrides)
    return entry


def test_parses_a_complete_entry() -> None:
    spec = parse_dataset_spec(valid_entry())

    assert spec == DatasetSpec(
        name="example-corpus",
        source="https://example.org/data",
        license="MIT",
        commercial_use=True,
        attribution_required=False,
    )
    assert spec.attribution_text() is None


@pytest.mark.parametrize(
    "field",
    ["name", "source", "license", "commercial_use", "attribution_required"],
)
def test_missing_required_field_is_rejected(field: str) -> None:
    entry = valid_entry()
    del entry[field]

    with pytest.raises(DatasetLicenseError, match=field):
        parse_dataset_spec(entry)


@pytest.mark.parametrize(
    "license_value",
    ["unknown", "UNKNOWN", "  Unknown  ", "tbd", "n/a", "none", "?", ""],
)
def test_unknown_license_is_rejected(license_value: str) -> None:
    with pytest.raises(DatasetLicenseError, match=r"not been established|non-empty"):
        parse_dataset_spec(valid_entry(license=license_value))


def test_non_boolean_flag_is_rejected() -> None:
    with pytest.raises(DatasetLicenseError, match="must be true or false"):
        parse_dataset_spec(valid_entry(commercial_use="yes"))


def test_attribution_required_without_text_is_rejected() -> None:
    with pytest.raises(DatasetLicenseError, match="attribution"):
        parse_dataset_spec(valid_entry(attribution_required=True))


def test_attribution_required_with_text_is_accepted() -> None:
    spec = parse_dataset_spec(
        valid_entry(
            attribution_required=True,
            attribution="example-corpus by Example Authors, MIT License",
        )
    )

    assert spec.attribution_text() == ("example-corpus by Example Authors, MIT License")


def test_error_message_names_the_dataset() -> None:
    entry = valid_entry(name="my-dataset")
    del entry["license"]

    with pytest.raises(DatasetLicenseError, match="my-dataset"):
        parse_dataset_spec(entry, index=3)


def test_error_message_falls_back_to_index() -> None:
    with pytest.raises(DatasetLicenseError, match="index 2"):
        parse_dataset_spec({}, index=2)


def test_non_mapping_entry_is_rejected() -> None:
    with pytest.raises(DatasetLicenseError, match="expected a mapping"):
        parse_dataset_spec("just-a-name", index=0)  # type: ignore[arg-type]


def test_commercial_use_gate_blocks_non_commercial_dataset() -> None:
    spec = parse_dataset_spec(valid_entry(license="CC-BY-NC-4.0", commercial_use=False))

    check_dataset_licenses([spec], commercial_use_intended=False)

    with pytest.raises(DatasetLicenseError, match="commercial use is intended"):
        check_dataset_licenses([spec], commercial_use_intended=True)


def test_personal_data_gate_is_on_by_default() -> None:
    spec = parse_dataset_spec(valid_entry(contains_personal_data=True))

    with pytest.raises(DatasetLicenseError, match="personal data"):
        check_dataset_licenses([spec])

    check_dataset_licenses([spec], allow_personal_data=True)


def test_empty_dataset_list_passes() -> None:
    check_dataset_licenses([], commercial_use_intended=True)
