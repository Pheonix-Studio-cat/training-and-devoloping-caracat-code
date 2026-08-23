# Model Card: Caracat Code 🐈‍⬛

> **Status: pre-release.** No fine-tuning has been performed yet. At the time of
> writing, Caracat Code is the project and tooling around a base model, not a
> separately trained set of weights. This card describes what is actually true
> today and is updated when that changes.

## Model details

| Field | Value |
| --- | --- |
| Model name | Caracat Code |
| Base model | [`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next) by Qwen |
| Model type | Causal language model for code |
| License (this project's code) | Apache-2.0 — see `LICENSE` |
| License (base model) | Apache-2.0 as reported for the upstream model — see `THIRD_PARTY_LICENSES.md` for verification status |
| Repository (code) | `Pheonix-Studio-cat/training-and-devoloping-caracat-code` |
| Repository (model) | [`Chinook416/caracat_code`](https://huggingface.co/Chinook416/caracat_code) |
| Version | 0.1.0 (documentation only) |

**Caracat Code is based on Qwen3-Coder-Next by Qwen.** It was not trained from
scratch.

## Base model specifications

This project makes no independent claims about the base model's architecture.
Numbers such as parameter count, context length and benchmark results belong to
the upstream model and are documented on the
[upstream model card](https://huggingface.co/Qwen/Qwen3-Coder-Next).

Read them there. They are deliberately not restated here, because a copied
number that is never re-checked becomes a false claim the moment upstream
changes it.

## Intended use

Caracat Code is intended for software development work:

- code generation,
- code understanding and explanation,
- debugging,
- refactoring,
- optimization,
- coding-agent workflows.

### Out of scope

- Safety-critical decision-making without human review.
- Use as a source of legal, medical or financial advice.
- Generating code intended to attack, compromise or disrupt systems.
- Any use that violates the base model's license, third-party licenses or
  applicable law.

## Modifications relative to the base model

| Area | Status |
| --- | --- |
| Fine-tuning | None performed |
| Quantization | None performed |
| Architecture changes | None |
| Tokenizer changes | None |
| Prompt/system-prompt changes | None |

When a modification is made, it is recorded in this table together with the
training configuration used, and the corresponding entry is added to
`THIRD_PARTY_LICENSES.md` if new components or datasets were involved.

## Training data

None used by this project so far.

Datasets are only used when their license permits the intended use. Every
dataset must declare its source, license, commercial-use permission and
attribution requirement before training can start; this is enforced in code by
`src/caracat_code/datasets.py`. A dataset with an unknown license cannot be
used.

## Evaluation

No benchmark results are published for Caracat Code.

The project does not publish evaluation numbers until they are produced by a
reproducible run recorded via `src/caracat_code/evaluation.py`, which captures
model version, base model version, quantization, hardware, software versions,
test set, generation parameters and context length alongside the results.

No claim is made that Caracat Code performs better than any other model.

## Limitations and risks

Caracat Code inherits the limitations of its base model, including:

- generated code may be incorrect, insecure or subtly wrong while looking
  plausible;
- it may produce output resembling code it was trained on, which can carry
  third-party rights;
- it has no awareness of your repository's licensing, security policy or
  runtime environment unless that context is supplied;
- output quality varies with prompt quality, language and task familiarity.

**Review generated code before running it.** Treat security-relevant output as
untrusted until reviewed.

## Responsible use

- Do not present generated code as free of third-party rights without review.
- Do not use the model to produce malware, credential-harvesting tooling or
  other abusive software.
- Keep humans in the loop for anything that touches production systems, user
  data or money.

## What this card does not cover: Caracat AI

The project also offers **Caracat AI**, a general assistant on a different base
model, `openai/gpt-oss-20b`. It has no card of its own because there is nothing
to describe: no weights, no training, no evaluation — it is a personality file
and an interface over someone else's model.

It is **not** a mode of Caracat Code, and nothing in this card applies to it.
Its licence position is unsettled; see `THIRD_PARTY_LICENSES.md`.

## Attribution

If you use or redistribute Caracat Code, preserve the attribution in `NOTICE`
and the license in `LICENSE`, and keep the reference to the upstream model:

> Caracat Code is based on Qwen3-Coder-Next by Qwen.

For the other assistant, the corresponding sentence is:

> Caracat AI is based on gpt-oss-20b by OpenAI.

## Contact

Issues and questions: the GitHub repository listed above.
