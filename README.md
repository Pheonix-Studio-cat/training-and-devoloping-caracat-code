# 🐈‍⬛ Caracat Code

**Caracat Code is an AI coding model based on Qwen3-Coder-Next by Qwen.**

This repository holds the development, training, evaluation and documentation
tooling for the model. The model itself is published at
[`Chinook416/caracat_code`](https://huggingface.co/Chinook416/caracat_code).

The project focuses on:

- code generation
- code understanding
- debugging
- refactoring
- optimization
- coding agents
- software development

> **Current status: pre-release.** No fine-tuning has been performed yet. What
> exists today is the project scaffolding, the legal documentation and the
> tooling that will record training and evaluation runs. See
> [`MODEL_CARD.md`](MODEL_CARD.md) for what is actually true about the model at
> any given time.

---

## What is whose

Keeping these four layers apart matters both legally and for anyone reading the
project's claims.

### 1. Qwen's original model

[`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next),
created and released by Qwen. All of its architecture, weights, training and
capabilities are Qwen's work. Its license — reported as Apache-2.0 — and its
notices govern that material. Caracat Code was **not** trained from scratch.

Architecture facts (parameter count, context length, benchmarks) belong to the
upstream model card and are not restated here.

### 2. Caracat Code's modifications

None yet. When fine-tuning, quantization or other changes are made, each one is
recorded in [`MODEL_CARD.md`](MODEL_CARD.md) with the configuration used.

### 3. Third-party components

Every external dependency — actions, libraries, datasets, assets — is listed
with its license and verification status in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

### 4. Project-specific code

Everything under `src/`, `scripts/`, `tests/` and `configs/` is original work of
this project, licensed under Apache-2.0 ([`LICENSE`](LICENSE)).

---

## Repository layout

```
CLAUDE.md                 operating rules for AI assistants working here
README.md                 this file
LICENSE                   Apache-2.0, for this project's own source code
NOTICE                    attribution, incl. the Qwen3-Coder-Next base model
MODEL_CARD.md             model documentation
THIRD_PARTY_LICENSES.md   third-party components and their licenses
SECURITY.md               vulnerability reporting and secret-handling policy
hf/                       exactly what is published to Hugging Face
src/caracat_code/         project library
scripts/                  train.py, evaluate.py entry points
configs/                  example training configurations
tests/                    pytest suite
.github/workflows/        ci.yml, sync-to-huggingface.yml
```

---

## Getting started

Requires Python 3.10 or newer.

```bash
pip install -e ".[dev]"

pytest                                   # run the test suite
ruff check . && ruff format --check .    # lint and format check
```

### Validating a training configuration

`scripts/train.py` does **not** run training yet. It loads a configuration,
validates it, and enforces the dataset license gate — so a configuration is
proven sound before any expensive run is wired up.

```bash
python scripts/train.py --config configs/example_training.yaml --validate-only
```

Every dataset in a configuration must declare `name`, `source`, `license`,
`commercial_use` and `attribution_required`. A dataset whose license is
`unknown` fails validation and training cannot start with it. This is
deliberate, and it is not to be worked around.

### Recording an evaluation run

`scripts/evaluate.py` writes a JSON report capturing everything needed to
reproduce a result: model version, base model version, quantization, hardware,
software versions, test set, generation parameters, context length and results.

```bash
python scripts/evaluate.py --dry-run --output-dir eval_runs
```

Fields that cannot be determined are recorded as `null` rather than guessed.

---

## Publishing to Hugging Face

`.github/workflows/sync-to-huggingface.yml` mirrors the **`hf/` directory only**
to `Chinook416/caracat_code` on every push to `main`.

This is an allowlist on purpose. The sync action mirrors deletions as well as
additions, so:

- anything you put in `hf/` becomes **public** on the next push to `main`;
- anything you remove from `hf/` is **removed** from the Hub.

Nothing outside `hf/` is ever uploaded. Model weights are not committed to git.

The workflow authenticates with the `HF_TOKEN` repository secret and fails with
a clear message if that secret is absent.

---

## Security

Never commit credentials of any kind — tokens, API keys, SSH keys or personal
data. Use GitHub Actions secrets. See [`SECURITY.md`](SECURITY.md).

---

## License

- **This project's source code:** Apache-2.0 — see [`LICENSE`](LICENSE).
- **Base model:** governed by the license under which Qwen distributes
  `Qwen/Qwen3-Coder-Next` — see [`NOTICE`](NOTICE) and
  [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
- **Third-party components:** see
  [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Commercial use may be possible, but it must satisfy Apache-2.0, every
third-party and dataset license, any model-specific terms, the relevant platform
terms and applicable law. No blanket claim is made that every component of
Caracat Code is commercially usable.

None of this is legal advice.

## Attribution

> Caracat Code is based on Qwen3-Coder-Next by Qwen.
