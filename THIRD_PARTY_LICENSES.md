# Third-Party Licenses

This file records every third-party component the Caracat Code project depends
on, together with its license and the terms that follow from it.

**How to read the "Verification" column**

| Marker | Meaning |
| --- | --- |
| ✅ Verified | The license text or an authoritative metadata source was read directly and is recorded below with the date and source. |
| ⚠️ Requires verification | The license is reported by a secondary source but was not read from the primary source. Do not rely on it for a legal decision until confirmed. |

Nothing in this file is legal advice. Where the status is ⚠️, the correct next
step is to read the primary source, not to assume.

---

## Base model

| Component | Source | License | Commercial use | Modification | Redistribution | Attribution required | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-Coder-Next | `Qwen/Qwen3-Coder-Next` on Hugging Face | Apache-2.0 (reported) | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Yes — §4(a)–(d) | ⚠️ Requires verification |

**Why this is not marked as verified:** the network egress proxy of the
environment in which this file was written blocks `huggingface.co`, so the
model page could not be read directly. Apache-2.0 is what secondary sources
report for this model. Before the first public release of Caracat Code, open
<https://huggingface.co/Qwen/Qwen3-Coder-Next>, read the `license` field and
any `LICENSE` file in the repository, and update this row.

**Obligations that follow if Apache-2.0 is confirmed:** keep the license text,
retain all upstream copyright/attribution/NOTICE content, and state prominently
that the files were modified where they have been. These are already reflected
in `NOTICE`.

---

## GitHub Actions used in CI

| Component | Source | License | Verification |
| --- | --- | --- | --- |
| `huggingface/hub-sync` | <https://github.com/huggingface/hub-sync> | Apache-2.0 | ✅ Verified 2026-08-16 — `LICENSE` on `main` read directly |
| `actions/checkout` | <https://github.com/actions/checkout> | MIT | ✅ Verified 2026-08-16 — `LICENSE` on `main` read directly |
| `actions/setup-python` | <https://github.com/actions/setup-python> | MIT | ✅ Verified 2026-08-16 — `LICENSE` on `main` read directly |

All three are pinned to a commit SHA in the workflow files so that the reviewed
code is the code that runs.

---

## Python dependencies

The base install of this project has one runtime dependency. Heavy ML
dependencies are deliberately absent — see "Not yet included" below.

| Component | Extra | License | Verification |
| --- | --- | --- | --- |
| PyYAML | runtime | MIT | ✅ Verified 2026-08-16 — PyPI metadata (`License :: OSI Approved :: MIT License`) |
| pytest | `dev` | MIT | ✅ Verified 2026-08-16 — PyPI metadata (`license_expression: MIT`) |
| ruff | `dev` | MIT | ✅ Verified 2026-08-16 — PyPI metadata (`license_expression: MIT`) |

---

## Not yet included

No training framework, no model weights and no dataset are part of this
repository yet.

When any of the following is added, a row must be added here **first**, with
the license read from the primary source:

- training/fine-tuning libraries (e.g. a trainer, a PEFT implementation, a
  serving runtime),
- quantization tooling,
- model weights or adapters of any origin,
- evaluation harnesses and their bundled test sets,
- **datasets** — these additionally require the checks in `CLAUDE.md` §
  "Datasets" (personal data, redistribution, commercial use, attribution).

"Open source" is not a license. "Available on the Hub" is not a license.
Identify the actual license before adding the dependency.

---

## Datasets

None used yet.

The dataset license gate in `src/caracat_code/datasets.py` enforces that every
dataset declared in a training configuration carries an explicit license,
source, commercial-use flag and attribution flag. A dataset whose license is
`unknown` cannot pass validation, so training cannot start with it.

---

## Change log for this file

| Date | Change |
| --- | --- |
| 2026-08-16 | Initial version: base model, GitHub Actions, Python dependencies. |
