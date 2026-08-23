# 🐈‍⬛ Caracat Code — Instructions for AI Coding Assistants

This file is the operating manual for any AI assistant working in this
repository. It condenses the project's master instructions into the rules that
change what you do. Read it before making changes.

**Default working mode:** inspect first → state the plan briefly → make the
smallest sensible change → test → review the diff → check security and
licensing → report what changed.

---

## 1. Project identity

| Field | Value |
| --- | --- |
| Project / model name | Caracat Code |
| Base model | `Qwen/Qwen3-Coder-Next` (Qwen) |
| Base license | Apache-2.0 (see `THIRD_PARTY_LICENSES.md` for verification status) |
| GitHub repo | `Pheonix-Studio-cat/training-and-devoloping-caracat-code` |
| Hugging Face repo | `Chinook416/caracat_code` |

Caracat Code is an AI coding model for code generation, code understanding,
debugging, refactoring, optimization and coding-agent workflows.

**Always say:** "Caracat Code is based on Qwen3-Coder-Next by Qwen."
**Never say** or imply that it was created independently of Qwen, or trained
from scratch.

### The second assistant

**Caracat AI** is a general assistant on a different base model,
`openai/gpt-oss-20b`. It is not a mode of Caracat Code and does not share its
name or its attribution.

**Always say:** "Caracat AI is based on gpt-oss-20b by OpenAI."
**Never** call it Caracat Code, never attribute it to Qwen, and never attribute
Caracat Code to OpenAI. Neither has its own weights: both are a personality and
an interface over someone else's model.

Its base model is **Apache-2.0**, read from the model page on 2026-08-23 and
recorded in `THIRD_PARTY_LICENSES.md`. The same obligations apply as for
Qwen3-Coder-Next: keep the licence text, retain upstream copyright,
attribution and NOTICE content, state where files were modified.

That settles one component, not the whole. `Qwen/Qwen3-Coder-Next` is still
⚠️ — so the rule in section 2 stands: never claim that all of Caracat Code is
commercially usable as a blanket statement.

Priority order when two goals conflict: correctness → security → stability →
code quality → maintainability → model quality → documentation → licensing
compliance → reproducibility → developer experience. Never trade away security
or legal compliance for speed.

---

## 2. Licensing — the rule that blocks work

Before adding **any** dependency, library, dataset, model, checkpoint, image,
snippet or other asset, determine all of the following:

1. source, 2. license, 3. commercial use, 4. modification, 5. redistribution,
6. attribution requirement, 7. additional notices, 8. model-specific
restrictions.

Then record it in `THIRD_PARTY_LICENSES.md` **in the same change** that adds the
dependency.

- "Open source" does not mean Apache-2.0.
- Publicly visible does not mean reusable.
- If the license is unclear: **stop and ask.** Do not assume permission.
- Do not invent legal facts. Where something is unconfirmed, write
  "License status requires verification" rather than guessing.

Upstream Apache-2.0 material keeps its notices. Never strip copyright, license
or attribution text from upstream files. `LICENSE` covers this project's own
source code; `NOTICE` records the base-model attribution; they are distinct and
must stay distinct.

Commercial use may be possible, but only if *every* component permits it. Never
state that all of Caracat Code is commercially usable as a blanket claim.

---

## 3. Secrets — never in the repository

Never commit passwords, API keys, Hugging Face tokens, GitHub tokens, Anthropic
or OpenRouter keys, SSH private keys, credentials or personal data.

- Use GitHub Actions secrets or environment variables.
- Never echo a secret into logs, and never inline one in YAML or source.
- Scan the diff for credentials before every commit.

---

## 4. Model and performance claims

Never invent benchmarks, parameter counts, training data, context lengths or
hardware requirements. Never claim Caracat Code beats another model without
evidence.

Facts about the base model belong to the upstream model card — link to it
rather than restating numbers that will drift.

Every evaluation run must record: model version, base model version,
quantization, hardware, software versions, test set, generation parameters
(including temperature), context length, results. Use
`src/caracat_code/evaluation.py`, which enforces this shape.

---

## 5. Datasets

Never train on arbitrary internet data.

Before using a dataset, establish source, license, commercial-use permission,
redistribution restrictions, attribution requirements, whether it contains
personal information, and whether it contains restricted or copyrighted
material.

A dataset with an unknown license is not used. `src/caracat_code/datasets.py`
enforces this: a declared dataset missing a license — or carrying `unknown` —
fails validation and training does not start. Do not weaken that gate to make a
run work.

---

## 6. Security

- Never introduce credential leaks, command injection, unjustified arbitrary
  code execution, insecure authentication, unsafe secret handling, backdoors or
  hidden telemetry.
- No hidden tracking of any kind.
- Review authentication, secret handling, workflows, user input handling and
  network requests before changing them.

### GitHub Actions specifics

- Set the minimum `permissions:` explicitly on every job.
- Pin third-party actions to a commit SHA with the version in a trailing
  comment.
- Never run untrusted code with elevated permissions or secret access.
- Guard workflows that need a secret so they fail fast with a clear message
  when it is missing, without touching the secret's value.

---

## 7. Hugging Face sync

`.github/workflows/sync-to-huggingface.yml` mirrors the **`hf/` directory only**
to `Chinook416/caracat_code`, using `HF_TOKEN` from repository secrets.

This is an allowlist by design: `huggingface/hub-sync` mirrors whatever it is
pointed at and **mirrors deletions**. Anything placed in `hf/` becomes public on
the next push to `main`; anything removed from `hf/` is removed from the Hub.

Before changing the sync or adding to `hf/`, verify: correct repository, correct
branch, correct files, correct model name, correct license and attribution, no
secrets, no private files, no debug or temporary files, no unauthorized
third-party material.

Keep the Hugging Face model card (`hf/README.md`) accurate and consistent with
`MODEL_CARD.md`.

A second workflow, `.github/workflows/sync-to-space.yml`, publishes the hosted
interface to a **static** Space: three files, assembled at build time —
`interface/index.html`, both files in `prompts/` and `space/README.md`. No
second copy is kept in git, so each personality and the page have one source. The
target Space is the repository variable `HF_SPACE_REPO_ID`, not a value written
into the workflow.

Static is a constraint, not a preference: only static Spaces are free, and the
project owner works from an iPad. A static Space runs nothing, so the workflow
refuses to publish anything that is not `.html` or `.md`.

The consequence to keep in mind when changing the page: **without a server the
API key lives in the visitor's browser.** Do not describe the hosted interface
as keeping the key server-side — that is true locally and false on the Space.
Running code, reading a project directory and fetching URLs are absent there
because nothing could perform them, and the page decides which mode it is in by
probing `/api/config` at startup rather than by a build flag.

---

## 7a. GitHub access

`src/caracat_code/github.py` reads public repositories and proposes changes to
them. Three rules govern any change to it:

- **The hosts are `api.github.com` and `raw.githubusercontent.com`, written into
  the module.** Never add a parameter that takes a host. That would turn it into
  an open proxy with a GitHub label.
- **Nothing commits to the default branch.** A change is a branch and a pull
  request. Do not add a path that bypasses that, in either the module or the
  page.
- **The model proposes, a person acts.** The interface may never send a change
  without an explicit press. Opening the confirmation panel must make no
  request.

Repository content is scanned for credentials before it is attached *and* before
it is committed. A public repository is not a reason to skip either.

---

## 8. Git workflow

Before major changes: check `git status`, the current branch, recent commits and
any existing uncommitted work. Never delete or overwrite the user's changes
without permission.

Before committing: read the diff, scan for secrets, check for stray files,
verify licenses, run the tests, update the documentation. Write meaningful
commit messages.

Do not open a pull request unless explicitly asked.

---

## 9. Documented changes

For every significant modification, state: what changed, why, which files,
whether licenses are affected, whether model behavior changes, whether the
Hugging Face repository needs updating, and whether workflows need updating.

No silent architectural changes. No large rewrites unless necessary.

---

## 10. When in doubt

If a legal, licensing or security question is unclear: identify the issue,
identify the relevant license or terms, explain the uncertainty, and ask the
project owner. Do not guess. This file is not legal advice.

If generated code looks copied from a specific third-party source, stop and
flag it.

---

## Repository layout

```
CLAUDE.md                 this file
README.md                 project overview
LICENSE                   Apache-2.0, for this project's own source code
NOTICE                    attribution, incl. the Qwen3-Coder-Next base model
MODEL_CARD.md             model documentation (GitHub copy)
THIRD_PARTY_LICENSES.md   every third-party component and its license
SECURITY.md               vulnerability reporting
docs/FINETUNING.md        worksheet to complete before a training run
hf/                       exactly what is published to the HF model repo
space/                    front matter and README for the static HF Space
interface/                the interface page — one file, two modes
prompts/                  the two personalities, as editable files
src/caracat_code/         project library (config, dataset gate, data prep, eval
                          recorder, interface, server, workspace, sandbox,
                          conversations, fetch, github, persona)
scripts/                  train.py, evaluate.py, prepare_dataset.py, serve_interface.py
configs/                  example training configurations
tests/                    pytest suite
.github/workflows/        ci.yml, sync-to-huggingface.yml, sync-to-space.yml
```

## Development commands

```bash
pip install -e ".[dev]"        # install with dev tooling
pytest                         # run the test suite
ruff check . && ruff format --check .
python scripts/train.py --config configs/example_training.yaml --validate-only
python scripts/evaluate.py --dry-run --output-dir eval_runs
python scripts/prepare_dataset.py --input examples.jsonl --output-dir data/run-01 ...

export CARACAT_API_KEY='...'          # never committed, never logged
python scripts/serve_interface.py --project-dir ~/proj   # the interface
```
