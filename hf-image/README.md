---
license: apache-2.0
base_model:
  - Tongyi-MAI/Z-Image-Turbo
pipeline_tag: text-to-image
library_name: diffusers
tags:
  - text-to-image
  - image-generation
---

# 🐈‍⬛ Caracat AI — image generation

**Image generation in Caracat AI is based on Z-Image-Turbo by Tongyi-MAI.**

> **There are no weights in this repository.** This card documents which model
> the Caracat project uses to generate images, and under what terms. It is not
> a copy of that model, not a fine-tune of it, and not a substitute for it.

Caracat AI is a general assistant. When it is asked for a picture, the request
goes from the visitor's own browser to
[`Tongyi-MAI/Z-Image-Turbo`](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
through an inference provider — never through the project's own server, and
never on the project's own credit.

Development happens on GitHub:
[`Pheonix-Studio-cat/training-and-devoloping-caracat-code`](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code)

## The three models behind Caracat

| | Model | By | For |
| --- | --- | --- | --- |
| **Caracat AI** | `openai/gpt-oss-20b` | OpenAI | conversation |
| **Caracat AI** | `Tongyi-MAI/Z-Image-Turbo` | Tongyi-MAI | images |
| **Caracat Code** | `Qwen/Qwen3-Coder-Next` | Qwen | programming |

None of them were trained by this project. Each is credited on the page that
uses it, beside every answer and beneath every image.

## Why images need the visitor's own key

An image costs a multiple of a text message. The project's shared allowance is
about sixteen messages for everyone together — two images would empty it.

So image generation appears only once a visitor has entered their own Hugging
Face key. Their request then travels straight from their browser to the
provider, on their own allowance, and the terms of their own account apply to
what they make.

## Model details

| Field | Value |
| --- | --- |
| Model used | `Tongyi-MAI/Z-Image-Turbo` by Tongyi-MAI |
| Its licence | Apache-2.0 — read from the model page on 2026-08-29 |
| Own weights | none |
| Fine-tuning performed | none |
| Version | 0.1.0 (documentation only) |

## Specifications

Parameter count, resolution, speed and benchmark results belong to
`Tongyi-MAI/Z-Image-Turbo` and are documented on its own card.

They are deliberately not restated here: a copied number that is never
re-checked becomes a false claim the moment upstream changes it.

## Intended use

Illustrating a conversation. Someone asks for a picture, and gets one.

### Out of scope

- Passing generated images off as photographs of real events.
- Images of identifiable real people presented as real.
- Anything violating the upstream model's licence and terms, the inference
  provider's terms, Hugging Face's terms, or applicable law.

**What is generated is the visitor's own doing**, on their own account and
their own key. This project neither stores generated images nor sees them: they
exist in the browser that asked for them and nowhere else.

## Limitations

Image models produce plausible-looking output that may be wrong in any detail —
hands, text, counts, physics, likenesses. Nothing generated should be treated
as a record of anything.

Quality varies with the prompt, and the model may simply not do what was asked.

## Licence and attribution

This repository's contents are provided under the Apache License 2.0; see
`LICENSE` and `NOTICE`.

`Tongyi-MAI/Z-Image-Turbo` remains governed by the licence under which
Tongyi-MAI distributes it. Commercial use may be possible, but it must satisfy
that licence, the inference provider's terms, platform terms and applicable
law. **No blanket claim of commercial usability is made.**

None of this is legal advice.

If you use or refer to this, keep the attribution:

> Image generation in Caracat AI is based on Z-Image-Turbo by Tongyi-MAI.
