---
license: apache-2.0
pipeline_tag: text-generation
library_name: transformers
language:
  - en
  - de
tags:
  - assistant
  - conversational
  - gpt-oss
---

# 🐈‍⬛ Caracat AI

**Caracat AI is based on gpt-oss-20b by OpenAI.**

> **There are no weights in this repository.** Caracat AI is a personality and
> an interface over someone else's model — not a fine-tune, not a copy, not a
> distinct set of parameters. This card documents what it actually is, and is
> updated when that changes.

> **Why this card does not declare a base model in its metadata.** Hugging Face
> reads a `base_model:` field as a *relation*, and its default is `finetune`.
> Declaring one put `base_model:finetune:` on this repository — a claim, in the
> machine-readable part of the card, that this is a fine-tune of that model,
> while the words above said it is not. The Hub offers `finetune`, `adapter`,
> `merge` and `quantized`; none of them is "a personality and an interface", so
> the field is left out and the relationship is stated in prose instead. A
> missing link in the model tree is a smaller loss than a false one.

Caracat AI is the general assistant of the Caracat project: it helps people
think, write, plan, learn and decide. Its sibling, **Caracat Code**, is a
separate assistant on a different base model and answers only about
programming.

| | Base model | For |
| --- | --- | --- |
| **Caracat AI** | [`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b) by OpenAI | everything |
| **Caracat Code** | [`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next) by Qwen | programming only |

Development happens on GitHub:
[`Pheonix-Studio-cat/training-and-devoloping-caracat-code`](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code)

Both assistants can be used, without an account, at the project's public site.

## What this repository contains

The personality, the licence position and the attribution. **No model files.**

If you want to run the underlying model, get it from
[`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b). Nothing here
substitutes for it, and nothing here is a modified version of it.

## Model details

| Field | Value |
| --- | --- |
| Name | Caracat AI |
| Base model | `openai/gpt-oss-20b` by OpenAI |
| Base model licence | Apache-2.0 — read from the model page on 2026-08-23 |
| Own weights | none |
| Fine-tuning performed | none |
| Version | 0.1.0 (documentation only) |

## Base model specifications

Parameter count, context length, architecture and benchmark results belong to
the base model and are documented on its own card.

They are deliberately not restated here: a copied number that is never
re-checked becomes a false claim the moment upstream updates it.

## How it behaves

The behaviour is a system prompt, kept as an editable file in the GitHub
repository (`prompts/caracat_ai_persona.md`) and loaded at run time. Its rules,
in short:

- **Ask instead of guessing.** Where an answer depends on something unknown,
  ask one focused question rather than inventing a plausible answer.
- **Never invent a fact, a source, a quotation, a number or a title.** Say when
  something is general knowledge rather than something you were told.
- **Reply in the language you were written to.**
- **Say plainly when a plan has a problem** rather than softening it away.
- **Be honest about limits**: for medical, legal and financial questions, say
  where a professional is needed; for anything turning on current facts, say
  that it cannot look anything up.

## Intended use

General assistance: explaining, drafting, planning, learning, thinking through
a decision.

### Out of scope

- Safety-critical decisions without human review.
- Acting as a substitute for a doctor, lawyer or financial adviser.
- Anything depending on current facts — it cannot browse and does not reliably
  know today's date.
- Any use violating the base model's licence, third-party licences or
  applicable law.

## Modifications relative to the base model

| Area | Status |
| --- | --- |
| Fine-tuning | None performed |
| Quantization | None performed |
| Architecture changes | None |
| Tokenizer changes | None |

The only thing this project adds is a system prompt and an interface.

## Training data

None. No training has been performed by this project.

Datasets would only be used where their licence permits it. Every dataset must
declare source, licence, commercial-use permission and attribution requirement
before a run can start; this is enforced in code in the GitHub repository. A
dataset with an unknown licence is not used.

## Evaluation

**No benchmark results are published for Caracat AI**, and none will be until
they come from a reproducible run that records model version, base model
version, quantization, hardware, software versions, test set, generation
parameters and context length alongside the numbers.

**No claim is made that Caracat AI performs better than any other model.**
Any measurable quality here is the base model's.

## Limitations and risks

Caracat AI inherits its base model's limitations:

- answers may be wrong while sounding confident;
- it has no access to current information and cannot look anything up;
- it does not know your situation beyond what you tell it;
- quality varies with the question, the language and the subject.

The system prompt asks it to say when it is unsure. That reduces the problem;
it does not remove it.

## Licence and attribution

This repository's contents are provided under the Apache License 2.0; see
`LICENSE` and `NOTICE`.

The base model remains governed by the licence under which OpenAI distributes
it. Commercial use may be possible, but it must satisfy Apache-2.0, all
third-party licences, any model-specific terms, platform terms and applicable
law. **No blanket claim of commercial usability is made for every component.**

None of this is legal advice.

If you use or refer to Caracat AI, keep the attribution:

> Caracat AI is based on gpt-oss-20b by OpenAI.

And do not confuse it with the other assistant:

> Caracat Code is based on Qwen3-Coder-Next by Qwen.
