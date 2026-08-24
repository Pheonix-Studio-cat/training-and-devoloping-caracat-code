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
| Qwen3-Coder-Next | `Qwen/Qwen3-Coder-Next` on Hugging Face | Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Yes — §4(a)–(d) | ✅ Verified 2026-08-23 |

**How this was verified:** the project owner opened
<https://huggingface.co/Qwen/Qwen3-Coder-Next> on 2026-08-23 and read the model
page's own `license` field, which shows `apache-2.0`. That is the primary
source.

It was *not* retrieved by this project's tooling — the network egress proxy of
the environment in which this file is written blocks `huggingface.co` — and the
route is recorded because it is part of the claim. The row says a person read
the primary source, not that a machine fetched it.

Between 2026-08-16 and this date the row stood at ⚠️ on the owner's word alone.
It was deliberately *not* closed while the neighbouring gpt-oss-20b row was
being closed, because closing a row in passing is exactly what the markers
exist to prevent.

**Obligations that follow:** keep the license text, retain all upstream
copyright/attribution/NOTICE content, and state prominently where files have
been modified. These are reflected in `NOTICE`.

---

## Second base model — Caracat AI

Caracat AI is a *second assistant* in this project: a personality and an
interface over a different base model. There are no Caracat weights for it
either.

| Component | Source | License | Commercial use | Modification | Redistribution | Attribution required | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-oss-20b | `openai/gpt-oss-20b` on Hugging Face | Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Yes — §4(a)–(d) | ✅ Verified 2026-08-23 |

**How this was verified:** the project owner opened
<https://huggingface.co/openai/gpt-oss-20b> on 2026-08-23 and read the model
page's own `license` field, which shows `apache-2.0`. That is the primary
source. It was *not* retrieved by this project's tooling — `huggingface.co` is
blocked by the network egress proxy of the environment this file is written in
— and the route matters enough to record, so the row claims exactly as much as
was actually checked.

**Obligations that follow.** Apache-2.0 permits commercial use, modification
and redistribution, and requires attribution: keep the license text, retain
upstream copyright, attribution and NOTICE content, and state where files have
been modified. `NOTICE` reflects this.

**What this repository ships:** no weights for this model. It sends requests to
an inference provider that serves it, so §4's redistribution obligations bite
on the provider's copy, not on anything here. They *do* bite on any copy of the
model made elsewhere — a duplicate under another account is a redistribution
and has to carry the upstream `LICENSE` and `NOTICE` unchanged.

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
| 2026-08-23 | Added `openai/gpt-oss-20b` for Caracat AI, verified Apache-2.0 from the model page. |
| 2026-08-23 | Closed the `Qwen/Qwen3-Coder-Next` row: Apache-2.0, read from the model page. Every component recorded in this file is now ✅. |

## What is settled, and what is not

**Every component recorded above is verified**, and each permits commercial use:
Apache-2.0 for both base models and `hub-sync`, MIT for the rest.

That is not the same as "Caracat Code is commercially usable", and the rule in
`CLAUDE.md` §2 against saying so still holds. Two things are simply not in this
file yet:

- **No dataset has been chosen.** Section 5 of `CLAUDE.md` and the gate in
  `src/caracat_code/datasets.py` mean an unknown-licence dataset cannot be used
  at all — but until one is chosen and recorded here, a training run's licence
  position is undetermined rather than clear.
- **No fine-tune exists.** There are no Caracat weights; both assistants are a
  personality over someone else's model. A fine-tune would add its own
  components and its own questions.

The blanket claim becomes safe when the file covers everything, not when the
rows it happens to contain are all green.
