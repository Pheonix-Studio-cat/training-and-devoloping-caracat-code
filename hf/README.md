---
license: apache-2.0
pipeline_tag: text-generation
library_name: transformers
language:
  - en
tags:
  - code
  - coding-agent
  - qwen3
  - code-generation
---

# 🐈‍⬛ Caracat Code

**Caracat Code is an AI coding model based on Qwen3-Coder-Next by Qwen.**

> **Status: pre-release.** No fine-tuning has been performed yet, and no weights
> are published in this repository. This model card documents the project, its
> base model and its licensing. It is updated when that changes — it does not
> describe capabilities the model does not yet have.

> **Why this card does not declare a base model in its metadata.** Hugging Face
> reads a `base_model:` field as a *relation*, and its default is `finetune`.
> Declaring one put `base_model:finetune:` on this repository — a claim, in the
> machine-readable part of the card, that this is a fine-tune of that model,
> while the words above said it is not. The Hub offers `finetune`, `adapter`,
> `merge` and `quantized`; none of them is "a personality and an interface", so
> the field is left out and the relationship is stated in prose instead. A
> missing link in the model tree is a smaller loss than a false one.

Development happens on GitHub:
[`Pheonix-Studio-cat/training-and-devoloping-caracat-code`](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code)

## Model details

| Field | Value |
| --- | --- |
| Model name | Caracat Code |
| Base model | [`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next) by Qwen |
| Model type | Causal language model for code |
| License | Apache-2.0 |
| Version | 0.1.0 (documentation only) |

Caracat Code was **not** trained from scratch. It derives from the upstream
model above, and the attribution and notices required by the upstream license
are preserved in the `NOTICE` file of this repository.

## Base model specifications

Parameter count, context length, architecture details and benchmark results
belong to the base model and are documented on the
[Qwen3-Coder-Next model card](https://huggingface.co/Qwen/Qwen3-Coder-Next).

They are deliberately not restated here: a copied number that is never
re-checked becomes a false claim the moment upstream updates it.

## Intended use

Software development work — code generation, code understanding and
explanation, debugging, refactoring, optimization, and coding-agent workflows.

### Out of scope

- Safety-critical decisions without human review.
- Legal, medical or financial advice.
- Producing code intended to attack, compromise or disrupt systems.
- Any use violating the base model's license, third-party licenses or
  applicable law.

## Modifications relative to the base model

| Area | Status |
| --- | --- |
| Fine-tuning | None performed |
| Quantization | None performed |
| Architecture changes | None |
| Tokenizer changes | None |

## Training data

None used by this project so far.

Datasets are only used where their license permits the intended use. Every
dataset must declare its source, license, commercial-use permission and
attribution requirement before a training run can start; this is enforced in
code in the GitHub repository. A dataset with an unknown license is not used.

## Evaluation

No benchmark results are published for Caracat Code.

Results are published only once produced by a reproducible run that records
model version, base model version, quantization, hardware, software versions,
test set, generation parameters and context length alongside the numbers.

**No claim is made that Caracat Code performs better than any other model.**

## Limitations and risks

Caracat Code inherits the limitations of its base model:

- generated code may be incorrect, insecure or subtly wrong while looking
  plausible;
- output may resemble code from training data, which can carry third-party
  rights;
- the model has no awareness of your repository's licensing, security policy or
  runtime environment unless that context is provided;
- quality varies with prompt quality, programming language and task
  familiarity.

**Review generated code before running it.** Treat security-relevant output as
untrusted until reviewed.

## Responsible use

- Do not present generated code as free of third-party rights without review.
- Do not use the model to produce malware, credential-harvesting tooling or
  other abusive software.
- Keep humans in the loop wherever production systems, user data or money are
  involved.

## License and attribution

This repository's contents are provided under the Apache License 2.0; see
`LICENSE` and `NOTICE`.

The base model remains governed by the license under which Qwen distributes it.
Commercial use may be possible, but it must satisfy Apache-2.0, all third-party
and dataset licenses, any model-specific terms, platform terms and applicable
law. No blanket claim of commercial usability is made for every component.

None of this is legal advice.

If you use or redistribute Caracat Code, keep the attribution:

> Caracat Code is based on Qwen3-Coder-Next by Qwen.
