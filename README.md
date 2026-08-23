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

Everything under `src/`, `scripts/`, `tests/`, `configs/`, `docs/` and
`interface/` is original work of this project, licensed under Apache-2.0
([`LICENSE`](LICENSE)). It is written against the standard library and plain
browser APIs, so it adds no dependencies and ships no third-party code.

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
docs/FINETUNING.md        worksheet to complete before a training run
hf/                       exactly what is published to the HF model repo
space/                    front matter and README for the static HF Space
interface/                the interface page — the same file in both modes
prompts/                  the two personalities, as editable files
src/caracat_code/         project library
scripts/                  train.py, evaluate.py, prepare_dataset.py, serve_interface.py
configs/                  example training configurations and dataset
tests/                    pytest suite
.github/workflows/        ci.yml, sync-to-huggingface.yml, sync-to-space.yml
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

### Preparing a fine-tune

Work through [`docs/FINETUNING.md`](docs/FINETUNING.md) first. It is a worksheet,
not a tutorial: goal, method, data, hardware, cost, measurement and stop
conditions, each with a blank that has to be filled in before GPU time is paid
for.

Turn raw examples into a checked training set:

```bash
python scripts/prepare_dataset.py \
    --input my_examples.jsonl \
    --output-dir data/run-01 \
    --name my-examples \
    --source "hand-written, own work" \
    --license Apache-2.0 \
    --commercial-use yes \
    --attribution-required no
```

Accepts `{"instruction", "input", "output"}` or `{"messages": [...]}` per line —
see [`configs/example_dataset.jsonl`](configs/example_dataset.jsonl). It checks
the structure, removes exact duplicates, splits off a validation set with a fixed
seed, and writes a manifest recording the counts, the license and a hash of the
input, so it stays clear later what a run was trained on.

**It refuses to write anything if the data contains something that looks like a
credential.** A key that reaches the training data ends up in the weights, and it
cannot be deleted from them — rotating it is the only remedy, and you have to
notice first. The report names the line and the field, never the value. Obvious
placeholders such as `your-api-key-here` do not trip it.

The license questions have no defaults, on purpose. An unanswered licensing
question is not the same as "no".

Then validate a training configuration:

```bash
python scripts/train.py --config configs/lora_finetuning.yaml --validate-only
```

The `method:` block describes how the model is adapted — `lora`, `qlora` or
`full`. Adapter settings are rejected for `full`, and `full` produces a warning:
updating every weight of a model this size needs datacenter hardware, not a
single machine.

Training itself is still not implemented. That step needs training libraries,
and each one has to be recorded in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) with its license read from
the primary source first.

### Using Caracat Code

`scripts/serve_interface.py` starts the interface on your own machine.

```bash
export CARACAT_API_KEY='your-provider-key'
python scripts/serve_interface.py --project-dir ~/my-project
```

Then open <http://127.0.0.1:8765>.

What it can do beyond chatting:

| Feature | How |
|---|---|
| **Read your project** | `--project-dir <path>`; click a file in the sidebar to attach it |
| **Run Python** | a `Run` button on every Python block the model returns |
| **Keep conversations** | saved automatically, listed in the sidebar |
| **Compare two models** | the `compare` toggle answers the same question twice, side by side |
| **Fetch web pages** | URLs in your message are fetched and attached automatically |
| **Read GitHub repositories** | `--github-repo owner/name`, more than once for more than one |
| **Propose changes as pull requests** | a `Propose…` button on any block the model marks with a file |

#### Two assistants

There are two, and they are two different assistants rather than two moods of
one — different base models, different scope, different names:

| | Base model | For |
| --- | --- | --- |
| **Caracat Code** | Qwen3-Coder-Next by Qwen | programming, and nothing else |
| **Caracat AI** | gpt-oss-20b by OpenAI | everything else |

Each personality is an ordinary text file in [`prompts/`](prompts/) — edit a
line, reload the page, and the behaviour changes. Each one states in its own
text which model it is based on, so the assistant answers that question
correctly without the interface having to tell it.

Their shared first rule is the one that matters most: **ask instead of
guessing**. `--persona chat` starts the local interface with Caracat AI; the
buttons under the system prompt switch between them.

**Caracat AI's licence position is not settled.** `openai/gpt-oss-20b` is
recorded in `THIRD_PARTY_LICENSES.md` as ⚠️ *requires verification*, because the
model page has not been read from a primary source. Read it before relying on
Caracat AI for anything that matters.

#### Working with GitHub

Public repositories, read without a token:

```bash
python scripts/serve_interface.py \
    --github-repo Pheonix-Studio-cat/training-and-devoloping-caracat-code \
    --github-repo some-owner/another-project
```

Each connected repository becomes a section in the sidebar; tapping a file
attaches it, labelled with the repository it came from, so a conversation about
two projects never leaves it unclear which file is which. **This works on the
hosted page too** — GitHub is one of the few APIs that permits a web page to
call it, which is why the Space can read a repository while it cannot fetch an
arbitrary URL.

The whole file tree arrives in one request, and file contents come from
`raw.githubusercontent.com`, which does not consume GitHub's hourly allowance.
Browsing costs one request, not one per file.

**Changing a repository** needs a token, and is deliberately awkward in exactly
one way: the model cannot do it. It marks a block with the file it belongs to —

````
```python file=src/app.py repo=owner/name
...the complete new contents...
```
````

— and the page offers a **Propose…** button. Pressing it creates a branch,
writes the file and opens a pull request. **Nothing is written to the default
branch**, in any mode: there is no function in `src/caracat_code/github.py` that
can, and one that tries is refused by name.

```bash
export CARACAT_GITHUB_TOKEN='...'   # fine-grained, only the repositories you name
```

Give the token *Contents* and *Pull requests* on read+write for exactly those
repositories, and nothing else. Locally it stays in the server process; there is
no flag for it, for the same reason there is none for the API key.

#### The limits, plainly

- **Running code is not a container.** Time, memory, output size and open files
  are capped, children are killed with the parent, and the run happens in a
  throwaway directory with an environment built from nothing — your API key is
  provably invisible to it. But the code runs as your user: it can reach the
  network and read what you can read. Don't run code you don't understand. The
  route only exists when the server is bound to a local address.
- **Your files are copied, never opened in place.** A wrong script destroys a
  copy. Files it created or changed are listed afterwards.
- **A file holding something credential-shaped is not sent.** Not to the
  provider, not into a run. The message names the line, never the value.
- **Fetching is automatic and internal addresses are blocked** — loopback,
  private ranges, and the cloud metadata address. Every redirect hop is
  re-checked. No credentials are ever attached to a fetch.
- **Conversations are stored outside the repository**, so they cannot be
  committed by accident.
- **GitHub is two fixed hosts**, `api.github.com` and
  `raw.githubusercontent.com`, written into the code rather than configurable.
  A repository file is scanned for credentials before it is attached and before
  it is committed — public is not the same as harmless.

**What it talks to.** No Caracat weights have been trained yet, so there is
nothing of our own to connect to. The interface speaks the OpenAI-compatible
chat-completions protocol, which means it works with any provider that serves
the base model — or with a local runtime:

```bash
# a hosted provider (default is https://router.huggingface.co/v1)
python scripts/serve_interface.py --api-base https://your-provider/v1

# a local runtime, e.g. Ollama or llama.cpp
python scripts/serve_interface.py --api-base http://localhost:11434/v1
```

The model list is fetched from whichever provider you point it at, so you pick
a real identifier from a dropdown instead of guessing one.

**Where the key lives.** In the environment, read once by the server process.
It is never sent to the browser, never written to a log, and there is
deliberately no `--api-key` flag, because a key passed on the command line ends
up in your shell history and in the process list. Anything a provider echoes
back in an error is redacted before it is shown. (Without a server this is
necessarily different — see [Running it without a computer](#running-it-without-a-computer).)

**What the server will and will not do.** It binds to `127.0.0.1` only and
warns loudly if you change that. It forwards exactly two upstream paths —
`chat/completions` and `models` — so it cannot be turned into an open proxy. It
validates every field of a chat request rather than passing it through, rejects
requests carrying a foreign `Host` header, and refuses plain `http` to anything
but a local endpoint. Model output is inserted into the page as text, never as
HTML.

### Recording an evaluation run

`scripts/evaluate.py` writes a JSON report capturing everything needed to
reproduce a result: model version, base model version, quantization, hardware,
software versions, test set, generation parameters, context length and results.

```bash
python scripts/evaluate.py --dry-run --output-dir eval_runs
```

Fields that cannot be determined are recorded as `null` rather than guessed.

### Running it without a computer

Everything above needs a server. On a tablet or a phone there isn't one — so the
page works without it, as a **static Hugging Face Space**: files are served, no
code runs, and the browser talks to your provider directly.

It is the *same* `interface/index.html` in both cases. Which mode applies is
discovered at startup rather than built in: the page asks its own origin for
`/api/config`, and if nothing answers with a real configuration, there is no
server and it switches. That also survives a host which answers unknown paths
with the page itself — a reply that is not the server's configuration counts as
no server.

1. Create a Space on Hugging Face with the **Static** SDK. Make it **private**
   unless you mean to share the page.
2. Add the Space's id (for example `Chinook416/caracat-code`) as the repository
   variable `HF_SPACE_REPO_ID` in this GitHub repository.
3. Push to `main`. `.github/workflows/sync-to-space.yml` publishes four files:
   the page, the two personalities it reads, and the Space's README.
4. Open the page and paste your provider key into *Settings*.

There is no Space secret, because a static Space runs nothing that could hold
one. Nothing is duplicated in git either — the workflow copies
`interface/index.html` and both files from `prompts/` at build time, so each
personality still has exactly one source.

#### What changes without a server

| | local | static Space |
|---|---|---|
| Chat, personality, model choice, comparison | ✅ | ✅ |
| Attach files | project directory | the browser's file picker |
| Keep conversations | on disk, outside the repo | in that browser |
| Read GitHub repositories | ✅ | ✅ |
| Propose changes as pull requests | ✅ | ✅ (see below) |
| Browse a project directory | ✅ | ❌ |
| Run Python | ✅ | ❌ |
| Fetch web pages | ✅ | ❌ |
| Where the API key lives | in the server process | **in the browser** |

The three missing rows are not switched off — there is nothing on a static host
that could do them.

**One uncertainty, stated rather than hidden.** Reading GitHub from the page is
measured and works. *Writing* from a page depends on GitHub accepting a
preflighted request from a browser; its documentation says it does, and this
could not be confirmed from the development environment, whose proxy answers
those requests itself. So the page tries, and if the browser refuses, it says
so and points at the local mode instead of failing silently. Running code and reading a project need a machine with your
files on it; fetching other sites is something a browser is not allowed to do.

**The key is the part to be deliberate about.** With no server there is nowhere
else to keep it: it is stored in the browser on that device and sent only to the
endpoint shown beside it. So keep such a Space private, give the key a spending
limit at your provider, and remember a key is revocable — *Forget the key on
this device* clears it locally, and revoking it at the provider is what actually
ends it.

If you would rather it never touched the browser, point the **Endpoint** field
at a small proxy of your own that holds the key. The page sends no
`Authorization` header when the endpoint is not the default provider, so that
works with no change here.

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
