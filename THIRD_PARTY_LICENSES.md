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
| Qwen3-Coder-Next | `Qwen/Qwen3-Coder-Next` on Hugging Face | Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Yes — §4(a)–(d) | ⚠️ Confirmed by the project owner; primary source not yet read |

**Status detail:** the project owner confirmed Apache-2.0 on 2026-08-16, and
secondary sources report the same. The upstream model page itself has not been
read directly — the network egress proxy of the environment in which this file
was written blocks `huggingface.co`.

To close this out, open <https://huggingface.co/Qwen/Qwen3-Coder-Next>, read the
`license` field and any `LICENSE` file in that repository, and change the marker
to ✅ Verified with the date. That is a two-minute check and it is the only
thing standing between this row and full verification.

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

Later additions deliberately kept this list unchanged:

- the local chat interface (`interface/`, `scripts/serve_interface.py`) uses only
  the Python standard library and plain browser APIs — no CDN scripts, no fonts,
  no stylesheets, no third-party code is loaded;
- the dataset preparation tooling (`src/caracat_code/data_prep.py`,
  `scripts/prepare_dataset.py`) uses only the standard library;
- so do the workspace, sandbox, conversation store and fetch modules added
  later. The whole interface is standard library plus plain browser APIs;
- the GitHub integration (`src/caracat_code/github.py`) uses `urllib` on the
  server and `fetch` in the browser. **No GitHub SDK or HTTP library was added**,
  which was a decision rather than an accident: a client for two endpoints is
  smaller than the licence review a dependency would require, and it keeps the
  reachable hosts something this repository states rather than inherits.

GitHub itself is a service this project talks to, not a component it ships.
Nothing of GitHub's is redistributed here, so there is no licence of theirs to
record — only their terms of use, which apply to whoever runs the interface.

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
