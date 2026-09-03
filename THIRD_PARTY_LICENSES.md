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

**Read again from the repository on 2026-09-03**, once Hugging Face became
reachable from this environment. The declaration holds: the card's front matter
says `license: apache-2.0` and the Hub carries the `license:apache-2.0` tag.
There is no `USAGE_POLICY` file, no gating and no `extra_gated_prompt`.

⚠️ **One oddity, recorded rather than smoothed over.** The card's front matter
also carries
`license_link: https://huggingface.co/Qwen/Qwen3-Coder-Next/blob/main/LICENSE`
— and **that file does not exist in the repository.** The listing has no
`LICENSE`, and asking for it directly returns nothing.

This does not undo the licence: the declaration is the `license` field and the
Hub tag, and both say `apache-2.0`. It does mean the text Qwen points at cannot
be read there, so the terms relied on are the Apache License 2.0 as published
by the Apache Software Foundation — the copy in this repository's own `LICENSE`
is that text. If Qwen intended a modified or supplemented licence at that
address, it is not visible, and the row would have to be reopened.

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

**A usage policy travels with it.** The upstream repository holds a
`USAGE_POLICY` file next to `LICENSE`. Read from the Hub on 2026-09-03, in
full, it says:

> We aim for our tools to be used safely, responsibly, and democratically,
> while maximizing your control over how you use them. By using OpenAI
> gpt-oss-20b, you agree to comply with all applicable law.

That is the whole of it. It adds no restriction beyond obeying the law, but it
is an additional notice within the meaning of §2 of `CLAUDE.md`, and it was
missing from this file until 2026-09-03 — the row was written from the model
page's `license` field alone, which does not show it. Anyone redistributing the
weights carries this file with them.

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

## Image model — pictures in Caracat AI

Caracat AI can generate pictures. It does not do so itself: the request goes to
a third model, and neither its weights nor a copy of them are in this
repository.

| Component | Source | License | Commercial use | Modification | Redistribution | Attribution required | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Z-Image-Turbo | `Tongyi-MAI/Z-Image-Turbo` on Hugging Face | Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Permitted under Apache-2.0 | Yes — §4(a)–(d) | ✅ Verified 2026-08-29 |

**How this was verified:** the project owner opened
<https://huggingface.co/Tongyi-MAI/Z-Image-Turbo> on 2026-08-29 and read the
model page's own `license` field, which shows `apache-2.0`. Same route as the
two base models above, and for the same reason — `huggingface.co` is blocked by
the network egress proxy of the environment this file is written in, so the row
claims that a person read the primary source, not that a machine fetched it.

The call address and the model id were read from the same page on the same day,
in its **View Code Snippets** panel.

✅ **The open item is closed: there is no acceptable-use policy.** On
2026-09-03 the repository was read directly from the Hub — the file listing and
the model card in full, 13,684 bytes, not truncated. The card's front matter
carries `license: apache-2.0` and nothing else bearing on use: no
`license_link`, no `extra_gated_prompt`, no gating, and no `USAGE_POLICY` file
of the kind `openai/gpt-oss-20b` ships. The body is a description of the model,
a model zoo table, code and citations.

This is a stronger route than the two rows above it: those record a person
reading a web page, this one records the repository's own contents. Recorded as
the difference it is.

**Obligations that follow.** Apache-2.0 permits commercial use, modification
and redistribution, and requires attribution: keep the license text, retain
upstream copyright, attribution and NOTICE content, and state where files have
been modified. `NOTICE` reflects this, and every picture the interface shows
names the model underneath it.

**`Chinook416/caracat_ai_image` is a model card, not a copy.** It holds
`hf-image/` and no weights, for the same reason `Chinook416/caracat_ai` does:
inference providers serve the upstream model, so a copy would be served by
nobody and would carry §4's redistribution obligations for no benefit at all.

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
| 2026-08-29 | Added `Tongyi-MAI/Z-Image-Turbo` for image generation, Apache-2.0 read from the model page. One open item recorded with it: whether the card also carries an acceptable-use policy. |
| 2026-09-03 | Hugging Face became reachable from this environment. Closed the Z-Image open item by reading the repository itself — no acceptable-use policy. Recorded `openai/gpt-oss-20b`'s `USAGE_POLICY`, which the model page's `license` field does not show and which this file had therefore missed. Recorded that `Qwen/Qwen3-Coder-Next` links to a `LICENSE` file it does not contain. |

## What is settled, and what is not

**Every component recorded above has its licence verified**, and each permits
commercial use: Apache-2.0 for the two base models, the image model and
`hub-sync`, MIT for the rest.

No item inside a verified row is open any more. The last one — whether the
image model carries an acceptable-use policy — was closed on 2026-09-03 by
reading the repository rather than the page, and the same pass found the
`USAGE_POLICY` that ships with `openai/gpt-oss-20b` and recorded it.

That second finding is the useful lesson: a model page's `license` field is not
the whole of a model's terms, and three rows here had been written from it
alone. They are now written from the repositories.

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
