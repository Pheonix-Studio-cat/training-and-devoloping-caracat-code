---
license: mit
pipeline_tag: text-generation
library_name: transformers
language:
  - en
  - de
tags:
  - assistant
  - conversational
  - deepseek
---

# 🐈‍⬛ Caracat Pro

**Caracat Pro is based on DeepSeek-V3.1 by DeepSeek.**

> **There are no weights in this repository.** Caracat Pro is a personality and
> an interface over someone else's model — not a fine-tune, not a copy, not a
> distinct set of parameters. This card documents what it actually is, and is
> updated when that changes.

> **Why this card does not declare a base model in its metadata.** Hugging Face
> reads a `base_model:` field as a *relation*, and its default is `finetune`.
> Declaring one puts `base_model:finetune:` on this repository — a claim, in the
> machine-readable part of the card, that this is a fine-tune of that model,
> while the words above say it is not. The Hub offers `finetune`, `adapter`,
> `merge` and `quantized`; none of them is "a personality and an interface", so
> the field is left out and the relationship is stated in prose instead. A
> missing link in the model tree is a smaller loss than a false one.

Caracat Pro is the largest of the project's three assistants, meant for the
questions the others find hard: long reasoning, several constraints at once,
problems where the first plausible answer is usually the wrong one.

| | Base model | For |
| --- | --- | --- |
| **Caracat Pro** | [`deepseek-ai/DeepSeek-V3.1`](https://huggingface.co/deepseek-ai/DeepSeek-V3.1) by DeepSeek | the hard questions |
| **Caracat AI** | [`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b) by OpenAI | everything |
| **Caracat Code** | [`Qwen/Qwen3-Coder-Next`](https://huggingface.co/Qwen/Qwen3-Coder-Next) by Qwen | programming only |

Development happens on GitHub:
[`Pheonix-Studio-cat/training-and-devoloping-caracat-code`](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code)

## It costs more, and the site says so

Caracat Pro is only offered to visitors who have entered a Hugging Face key of
their own. That is not a paywall — the other two assistants are free to use on
the public site — it is arithmetic: DeepSeek-V3.1 is a far larger model, and a
message to it costs a multiple of a message to a 20B one.

The personality is written to say so. Asked something small, it will point at
Caracat AI rather than quietly spending someone else's credit.

## What this repository contains

The personality, the licence position and the attribution. **No model files.**

If you want to run the underlying model, get it from
[`deepseek-ai/DeepSeek-V3.1`](https://huggingface.co/deepseek-ai/DeepSeek-V3.1).
Nothing here substitutes for it, and nothing here is a modified version of it.

## Model details

| Field | Value |
| --- | --- |
| Name | Caracat Pro |
| Base model | `deepseek-ai/DeepSeek-V3.1` by DeepSeek |
| Base model licence | MIT — read from the repository on 2026-09-05 |
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
repository (`prompts/caracat_pro_persona.md`) and loaded at run time. Its
rules, in short:

- **Ask instead of guessing.** A larger model does not soften this — it makes a
  wrong answer more convincing, which is a reason for more care, not less.
- **Take the question apart before answering it**: name the assumptions, weigh
  the approaches, say which parts are uncertain.
- **Never invent a fact, a source, a quotation, a number or a title.**
- **Reply in the language you were written to.**
- **Say plainly when a plan has a problem** rather than softening it away.
- **Send small jobs to the cheaper assistant.**

## Intended use

General assistance where the question is genuinely hard: explaining, drafting,
planning, thinking a decision through under several constraints at once.

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

**No benchmark results are published for Caracat Pro**, and none will be until
they come from a reproducible run that records model version, base model
version, quantization, hardware, software versions, test set, generation
parameters and context length alongside the numbers.

**No claim is made that Caracat Pro performs better than any other model** —
including the project's own two. It runs on a larger base model; that is a fact
about the base model, not a measured result here.

## Limitations and risks

Caracat Pro inherits its base model's limitations:

- answers may be wrong while sounding confident, and a larger model sounds more
  confident;
- it has no access to current information and cannot look anything up;
- it does not know your situation beyond what you tell it;
- quality varies with the question, the language and the subject.

The system prompt asks it to say when it is unsure. That reduces the problem;
it does not remove it.

## Licence and attribution

This repository's contents are provided under the **MIT licence**; see
`LICENSE` and `NOTICE`.

That matches the base model. DeepSeek publishes DeepSeek-V3.1 under MIT, and
this card is offered under the same terms rather than under a stricter licence
than the thing it documents.

**It is the only part of the project under MIT.** The GitHub repository's own
`LICENSE` is Apache-2.0 and covers everything else — the tooling, the tests,
the other two cards. This directory is the exception, and it is written down
here so nobody has to infer it.

**MIT carries a single condition:** the copyright notice and the permission
notice must accompany copies or substantial portions of the software. There is
no obligation to state changes, no NOTICE requirement and no express patent
grant — those belong to Apache-2.0, which governs the other two base models
and the rest of this project.

This repository copies no weights, so the condition attaches to nothing here as
far as the model goes. It does attach to this card's own text, and it would
attach to anyone who redistributes the model itself.

Commercial use may be possible, but it must satisfy the MIT licence, all
third-party licences, any model-specific terms, platform terms and applicable
law. **No blanket claim of commercial usability is made for every component.**

None of this is legal advice.

If you use or refer to Caracat Pro, keep the attribution:

> Caracat Pro is based on DeepSeek-V3.1 by DeepSeek.

And do not confuse it with its siblings:

> Caracat AI is based on gpt-oss-20b by OpenAI.
>
> Caracat Code is based on Qwen3-Coder-Next by Qwen.
