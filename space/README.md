---
title: Caracat Code
emoji: 🐈‍⬛
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: apache-2.0
short_description: A coding assistant based on Qwen3-Coder-Next.
---

# 🐈‍⬛ Caracat Code

**Caracat Code is an AI coding assistant based on Qwen3-Coder-Next by Qwen.**

This Space is the hosted interface, served as a static page. There is no server
here — the page in your browser talks to your provider directly.

> No Caracat weights have been trained yet. The model answering here is the base
> model; what makes it Caracat Code is the personality and the tooling around
> it. See the [model repository](https://huggingface.co/Chinook416/caracat_code)
> for the current state.

## Setting it up

1. Open **Settings** on the page. The **Endpoint** starts on Hugging Face's
   OpenAI-compatible router, `https://router.huggingface.co/v1`.
2. Paste an access token into **API key**. A Hugging Face token with the
   *Inference Providers* permission works here. It is stored in your browser and
   sent only to the endpoint above.
3. Pick a model from the dropdown. The list comes from the endpoint.

There is no Space secret to configure, because a static Space runs no code that
could hold one.

**If the model list stays empty and the browser console mentions CORS**, that
endpoint does not accept requests from a web page, and no setting here can
change that — a browser may only call an API that opts in. Two ways on:

- use an endpoint that does permit browser calls, entered in the same field; or
- put a small proxy of your own in front, which is also how the key stops
  living in the browser (see below).

## Where the key lives, plainly

**In your browser, on your device.** Not in this repository, not in the page's
source, and not on any server of ours — but it is on the device, in the
browser's local storage, until you press *Forget the key on this device*.

Three things follow from that, and none of them are optional:

- **Keep this Space private** unless you mean to share the page. It is the page
  that is shared, never your key — but a private Space is one less thing to
  think about.
- **Give the key a spending limit** at your provider. Then the worst case is
  bounded rather than open-ended.
- **A key is revocable.** If it may have been seen, revoke it and make a new
  one. It is worth nothing except the credit behind it.

If you would rather the key never touched the browser at all, point the
**Endpoint** field at a small proxy of your own that holds the key and forwards
the request. The page sends no `Authorization` header when the endpoint is not
the default provider, so such a proxy works without any change here.

## What this Space can and cannot do

| | |
| --- | --- |
| Chat, with the personality applied | ✅ |
| Choose from your provider's models | ✅ |
| Compare two models side by side | ✅ |
| Attach files from your device | ✅ — through the browser's file picker |
| Keep conversations | ✅ — in this browser, not on a server |
| Read GitHub repositories | ✅ — public ones, no token needed |
| Propose changes as pull requests | ✅ — with a GitHub token, and only on a press |
| Browse a project directory | ❌ — that needs a server with your files on it |
| Run code | ❌ — that needs a server too |
| Fetch web pages | ❌ — a browser is not allowed to read other sites |

The four missing pieces are not switched off; there is simply nothing here that
could do them. For those, run the interface on your own machine:

```bash
export CARACAT_API_KEY='...'
python scripts/serve_interface.py --project-dir ~/your-project
```

Then the key stays in that server process and never reaches the page, the
project directory is readable, and Python can be run under limits.

## Working with GitHub

Add repositories in **Settings** as `owner/name`, one per line. Public ones need
no token, and each becomes its own section in the sidebar — attach a file and it
carries the repository in its name, so a conversation about two projects stays
clear about which file is which.

This works here, unlike fetching an ordinary web page, because GitHub is one of
the few APIs that permits a web page to call it.

**To let it propose changes**, add a GitHub token in Settings. Make it
fine-grained, limited to exactly those repositories, with *Contents* and *Pull
requests* on read+write and nothing else. Then a block the model marks with a
file gets a **Propose…** button:

- pressing it creates a branch and opens a pull request — never a commit to the
  default branch;
- opening the confirmation panel sends nothing at all; only the button does;
- the model can propose but cannot act. That separation is the point.

The token lives in this browser, like the API key, with the same *Forget* button.

**Attached files are checked before they are sent.** A file that looks like it
holds a credential is refused, and the message names the line, never the value.
Sending a key to a provider cannot be undone.

## The personality

It lives in an ordinary text file, `prompts/caracat_persona.md`, in the
[GitHub repository](https://github.com/Pheonix-Studio-cat/training-and-devoloping-caracat-code),
and is published next to this page as `caracat_persona.md`. Edit a line there,
and this Space picks it up on the next sync.

Its first rule is the one that matters most: **ask instead of guessing.** When
an answer depends on something it does not know, it asks one focused question
rather than inventing an answer that happens to fit.

## Attribution

> Caracat Code is based on Qwen3-Coder-Next by Qwen.

Licensed under Apache-2.0. The base model remains governed by the license under
which Qwen distributes it. See `NOTICE` and `THIRD_PARTY_LICENSES.md` in the
GitHub repository.
