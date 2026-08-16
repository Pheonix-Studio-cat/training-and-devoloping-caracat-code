"""Dataset declarations and the license gate that guards training runs.

The project rule is simple: a dataset whose license is unknown is not used.
This module turns that rule into code, so it fails at configuration-load time
rather than being discovered after a training run has produced weights of
uncertain provenance.

Every dataset in a training configuration must declare:

``name``, ``source``, ``license``, ``commercial_use``, ``attribution_required``

and, when ``attribution_required`` is true, the attribution text to reproduce.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

__all__ = [
    "DatasetLicenseError",
    "DatasetSpec",
    "check_dataset_licenses",
    "parse_dataset_spec",
]

REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "source",
    "license",
    "commercial_use",
    "attribution_required",
)
"""Fields every dataset entry must declare explicitly."""

UNKNOWN_LICENSE_VALUES: frozenset[str] = frozenset(
    {
        "",
        "?",
        "n/a",
        "na",
        "none",
        "tbd",
        "to be determined",
        "unclear",
        "unknown",
        "unspecified",
    }
)
"""Values that mean "we have not established the license". None of them pass."""


class DatasetLicenseError(ValueError):
    """Raised when a dataset declaration is incomplete or not licensed for use."""


@dataclass(frozen=True)
class DatasetSpec:
    """A dataset with its provenance and license terms established up front."""

    name: str
    source: str
    license: str
    commercial_use: bool
    attribution_required: bool
    attribution: str | None = None
    contains_personal_data: bool | None = None
    notes: str | None = None

    def attribution_text(self) -> str | None:
        """The attribution to reproduce, or ``None`` if none is required."""
        return self.attribution if self.attribution_required else None


def _describe(index: int | None, name: object = None) -> str:
    """A human-readable label for error messages about a dataset entry."""
    if isinstance(name, str) and name:
        return f"dataset {name!r}"
    if index is not None:
        return f"dataset at index {index}"
    return "dataset"


def parse_dataset_spec(
    raw: Mapping[str, object], index: int | None = None
) -> DatasetSpec:
    """Build a :class:`DatasetSpec` from a mapping, enforcing the license gate.

    Args:
        raw: The dataset entry as read from a configuration file.
        index: Position in the dataset list, used in error messages.

    Raises:
        DatasetLicenseError: If a required field is missing, a flag is not a
            boolean, the license is unknown, or a required attribution is
            absent.
    """
    if not isinstance(raw, Mapping):
        raise DatasetLicenseError(
            f"{_describe(index)}: expected a mapping of fields, "
            f"got {type(raw).__name__}"
        )

    label = _describe(index, raw.get("name"))

    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise DatasetLicenseError(
            f"{label}: missing required field(s): {', '.join(missing)}. "
            "Every dataset must declare its source and license terms before it "
            "can be used for training."
        )

    for field in ("name", "source", "license"):
        value = raw[field]
        if not isinstance(value, str) or not value.strip():
            raise DatasetLicenseError(
                f"{label}: field {field!r} must be a non-empty string, got {value!r}"
            )

    for field in ("commercial_use", "attribution_required"):
        value = raw[field]
        if not isinstance(value, bool):
            raise DatasetLicenseError(
                f"{label}: field {field!r} must be true or false, got {value!r}. "
                "An unanswered license question is not a default -- establish "
                "the answer from the dataset's license."
            )

    license_name = str(raw["license"]).strip()
    if license_name.lower() in UNKNOWN_LICENSE_VALUES:
        raise DatasetLicenseError(
            f"{label}: license is {license_name!r}, which means it has not been "
            "established. A dataset with an unknown license is not used. "
            "Identify the license from the primary source, record it in "
            "THIRD_PARTY_LICENSES.md, then declare it here."
        )

    attribution_required = bool(raw["attribution_required"])
    attribution = raw.get("attribution")
    if attribution is not None and not isinstance(attribution, str):
        raise DatasetLicenseError(
            f"{label}: field 'attribution' must be a string, got {attribution!r}"
        )
    if attribution_required and not (attribution or "").strip():
        raise DatasetLicenseError(
            f"{label}: 'attribution_required' is true, so 'attribution' must "
            "contain the attribution text to reproduce."
        )

    contains_personal_data = raw.get("contains_personal_data")
    if contains_personal_data is not None and not isinstance(
        contains_personal_data, bool
    ):
        raise DatasetLicenseError(
            f"{label}: field 'contains_personal_data' must be true or false, "
            f"got {contains_personal_data!r}"
        )

    notes = raw.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise DatasetLicenseError(
            f"{label}: field 'notes' must be a string, got {notes!r}"
        )

    return DatasetSpec(
        name=str(raw["name"]).strip(),
        source=str(raw["source"]).strip(),
        license=license_name,
        commercial_use=bool(raw["commercial_use"]),
        attribution_required=attribution_required,
        attribution=attribution.strip() if isinstance(attribution, str) else None,
        contains_personal_data=contains_personal_data,
        notes=notes,
    )


def check_dataset_licenses(
    datasets: Iterable[DatasetSpec],
    *,
    commercial_use_intended: bool = False,
    allow_personal_data: bool = False,
) -> None:
    """Check a set of datasets against the intended use of the trained model.

    ``parse_dataset_spec`` establishes that each dataset's terms are known.
    This function checks those terms against what the run intends to do.

    Args:
        datasets: The declared datasets.
        commercial_use_intended: If true, every dataset must permit commercial
            use.
        allow_personal_data: If true, datasets flagged as containing personal
            data are permitted. Off by default.

    Raises:
        DatasetLicenseError: If any dataset does not permit the intended use.
    """
    specs = list(datasets)

    if commercial_use_intended:
        blocked = [spec.name for spec in specs if not spec.commercial_use]
        if blocked:
            raise DatasetLicenseError(
                "commercial use is intended, but these datasets do not permit "
                f"it: {', '.join(blocked)}. Either remove them or set "
                "'commercial_use_intended: false' for this run."
            )

    if not allow_personal_data:
        flagged = [spec.name for spec in specs if spec.contains_personal_data]
        if flagged:
            raise DatasetLicenseError(
                "these datasets are flagged as containing personal data: "
                f"{', '.join(flagged)}. Review the legal basis for processing "
                "it, then set 'allow_personal_data: true' deliberately if it is "
                "permitted."
            )
