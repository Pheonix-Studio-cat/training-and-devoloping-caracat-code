---
title: Caracat Code
emoji: 🐈‍⬛
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: A coding assistant based on Qwen3-Coder-Next, with a personality you can edit.
---

# 🐈‍⬛ Caracat Code

**Caracat Code is an AI coding assistant based on Qwen3-Coder-Next by Qwen.**

This Space is the hosted interface. It talks to an OpenAI-compatible provider
using the `CARACAT_API_KEY` secret configured on the Space — the key stays in
the server process and is never sent to your browser.

> No Caracat weights have been trained yet. The model answering here is the base
> model; what makes it Caracat Code is the personality and the tooling around
> it. See the [model repository](https://huggingface.co/Chinook416/caracat_code)
> for the current state.

## Setting it up

1. **Add the secret.** *Settings → Variables and secrets → New secret*, named
   `CARACAT_API_KEY`, holding your provider's API key.
   Add it as a **secret**, not a variable — a variable is readable by anyone who
   can see the Space.
2. Optionally set `CARACAT_API_BASE` if your provider is not the default, and
   `CARACAT_MODEL` to preselect a model.
3. Restart the Space.

**Make the Space private unless you mean to share it.** Anyone who can open a
public Space can send requests through it, and every request is billed to your
provider account.

## What this Space can and cannot do

| | |
| --- | --- |
| Chat, with the personality applied | ✅ |
| Choose from your provider's models | ✅ |
| Compare two models side by side | ✅ |
| Read files from a project | ❌ — your files are on your machine, not here |
| Run code | ❌ — impossible by design, see below |
| Store conversations | ❌ — one server, many visitors; chats stay in your tab |

**Running code is not merely switched off.** The route only exists when the
server is bound to a local address, and a container never is. Without that rule,
anyone who found this address could execute programs here.

For the file access and the sandbox, run the interface on your own machine:

```bash
export CARACAT_API_KEY='...'
python scripts/serve_interface.py --project-dir ~/your-project
```

## The personality

It lives in an ordinary text file, `prompts/caracat_persona.md`, in the
[GitHub repository](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code).
Edit a line there, and this Space picks it up on the next sync.

Its first rule is the one that matters most: **ask instead of guessing.** When
an answer depends on something it does not know, it asks one focused question
rather than inventing an answer that happens to fit.

## Attribution

> Caracat Code is based on Qwen3-Coder-Next by Qwen.

Licensed under Apache-2.0. The base model remains governed by the license under
which Qwen distributes it. See `NOTICE` and `THIRD_PARTY_LICENSES.md` in the
GitHub repository.
