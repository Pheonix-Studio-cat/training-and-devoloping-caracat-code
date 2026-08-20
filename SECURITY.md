# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately. Do **not** open a public issue for a
security problem.

Use GitHub's private vulnerability reporting on this repository
(*Security → Report a vulnerability*), or contact the repository owner directly.

Please include what you did, what happened, what you expected, and — if you
have one — a minimal reproduction. Expect an acknowledgement; please allow time
for a fix before disclosing publicly.

## Secrets

No credential of any kind belongs in this repository. That includes API keys,
Hugging Face tokens, GitHub tokens, SSH private keys, passwords and personal
data.

- Secrets live in GitHub Actions secrets or in the local environment.
- Workflows reference them as `${{ secrets.NAME }}` and never echo their value.
- Every diff is scanned for credentials before it is committed.

**If a secret is ever committed:** revoke and rotate it first, then remove it
from the repository. Rewriting history does not un-leak a token that has already
been pushed — rotation is the fix, cleanup is the follow-up.

This project uses two secrets, and neither is ever stored in the repository:

- `HF_TOKEN` — a GitHub Actions secret, consumed by
  `.github/workflows/sync-to-huggingface.yml` to publish the `hf/` directory to
  the Hugging Face model repository. It should be a write-scoped token limited
  to that model repository.
- `CARACAT_API_KEY` — a local environment variable, read by
  `scripts/serve_interface.py` to reach an inference provider. It stays in that
  process: the browser never receives it, it is never logged, and it is
  redacted out of any provider error before it is displayed. There is no
  command-line flag for it, so it does not land in your shell history.

**Neither secret exists on the static Space**, which is not an oversight — see
the next section.

## Without a server: the static Space

The same page runs in two places, and the difference is worth stating rather
than discovering. On your machine it talks to its own server. Published as a
Hugging Face **static** Space it talks to your provider directly, because a
static Space serves files and runs nothing.

**The key is then in the browser.** There is no other place for it: no process,
no secret store, no server-side configuration. It is written to the browser's
local storage on that device and sent only to the endpoint shown beside it in
Settings. This is a real reduction in protection compared with the local server,
and it is the reason the static Space is the fallback and not the default.

What follows from it, and what the page does about it:

- The page is served over `https`, and it **refuses a non-`https` endpoint**
  other than `localhost`, so the key is never sent in the clear.
- *Forget the key on this device* removes it from local storage. That is a local
  action; **revoking the key at the provider is what actually ends it**, and the
  message says so.
- Provider errors are shown with the key stripped out, in case one is echoed
  back.
- The key is only attached when the endpoint is the default provider or a key
  has been entered — so pointing the endpoint at a proxy that holds the key
  works without sending a second one.

**Keep such a Space private unless the page is meant to be shared,** and give
the key a spending limit at the provider. A public page does not expose your
key — the key is in *your* browser, not in the page — but a bounded key turns
every remaining scenario into a bounded one.

**Three capabilities are absent there, not disabled:** running code, reading a
project directory, and fetching URLs. Each needs a server, and there is none. The
mode is detected at startup, so this cannot be turned on by a misconfigured flag.

Reading GitHub is **not** among them: GitHub permits requests from a web page
where an arbitrary website does not, so the hosted page can read a repository
even though it cannot fetch a URL.

Files chosen through the browser's file picker are scanned in the page before
they are attached, with the same patterns the Python side uses. A file that
looks like it holds a credential is refused, and the message names the line and
the kind, never the value.

## GitHub

Reading a repository needs no credential; changing one does, and that write path
is built so the dangerous parts are impossible rather than discouraged.

**Two hosts, not a URL.** `src/caracat_code/github.py` talks to `api.github.com`
and `raw.githubusercontent.com`, written into the module. There is no parameter
that takes a host, so it cannot be pointed at anything else — the same reason
`fetch.py` blocks internal addresses, applied harder, because here nothing
legitimate points elsewhere. A test pins it, including the cloud metadata
address.

**Paths are refused, not repaired.** A path containing `..` or starting with `/`
is rejected before a request is made. An earlier version stripped `./` with
`lstrip("./")` — which removes those *characters* rather than that *prefix*, so
`../../etc/passwd` silently became `etc/passwd` and passed the traversal test it
should have failed. Quietly rewriting a suspicious path is worse than refusing
it, because nobody learns that it happened.

**Content is scanned in both directions.** A repository file is scanned before it
is attached to a conversation, and any new content is scanned before it is
committed. Public is not the same as harmless: forwarding a key to an inference
provider is a second disclosure, and a key committed to a public repository is
public immediately, with rotation the only cure. Findings name the line and the
kind, never the value.

**Never the default branch.** Every change becomes a new branch and a pull
request. No function in the module commits to the default branch, and one that
is asked to is refused by name — so the guarantee is structural rather than a
rule someone has to remember.

**The model proposes; a person decides.** A fenced block marked with a file
becomes a button. Opening the confirmation panel makes no request at all; only
pressing the button reaches GitHub. Model output is not trusted input, and this
is where that matters most.

**Where the token lives.** Locally, in the server process, read from
`CARACAT_GITHUB_TOKEN` — there is no command-line flag, for the same reason
there is none for the API key. On the static Space there is no process, so it is
in the browser like the provider key, with the same treatment: `https` only,
removable, redacted out of errors, never logged. Give it *Contents* and *Pull
requests* for exactly the repositories in use, and nothing else.

### The page loads nothing from anywhere else

`interface/index.html` declares a Content Security Policy that permits no
external script, stylesheet, font or image, and restricts network access to the
page's own origin, `https`, and a local runtime. Model output is inserted as
text nodes, never as HTML. The policy is there so that a later edit which
introduces a CDN dependency fails visibly instead of quietly working.

## Running code, reading files, fetching URLs

The interface can do three things that deserve stating outright.

**Running Python** caps CPU time, memory, output size, file size and open file
descriptors, kills the process group on timeout, uses a throwaway working
directory, and builds the child's environment from an allowlist so no secret in
your shell reaches it. It is **not a container**: the code runs as your user and
can reach the network and your files. The route is only registered when the
server is bound to a local address, so it cannot be exposed by forgetting a
flag.

**Reading project files** is confined to the one directory passed with
`--project-dir`. Paths are resolved before use, so `../` and symlinks pointing
outward are refused. Credential files are unreachable by name, and every file is
scanned before it is returned: a file that appears to hold a key is refused with
the line number, never the value. Sending a file to a provider cannot be undone.

**Fetching URLs** happens without a per-request confirmation, by the project
owner's decision. Internal addresses stay blocked regardless — loopback, private
ranges, link-local (including the cloud metadata address) — and every redirect
hop is re-checked. Only `http` and `https`; no credentials are attached;
responses are capped and must be text. The residual risk is stated in the
interface: model output is not trusted input, so every fetch is visible in the
conversation.

### The Host header rule

A local server refuses requests whose `Host` header is not a local name. That
stops a hostile page from pointing a hostname it controls at `127.0.0.1` and
driving a server meant for the person at the keyboard.

The rule applies **only** to a locally bound server. A server bound to a public
address — a Space, a container — is reached by its public name by design, and
refusing that name would reject every legitimate request while protecting
nothing. Both behaviours are covered by tests.

## Workflow permissions

Every workflow job declares the minimum `permissions:` it needs. Third-party
actions are pinned to a commit SHA so that the reviewed code is the code that
runs. The Hugging Face sync is restricted to the upstream repository so forks
cannot trigger it.

## Generated code

Code produced by AI tooling in this project — like any other contribution — is
reviewed before it is merged. Treat generated code that touches authentication,
secret handling, deserialization, subprocess execution or network requests as
requiring extra scrutiny.

## Scope

This policy covers the contents of this repository: tooling, configuration,
workflows and documentation. Vulnerabilities in the upstream base model or in
third-party dependencies should be reported to their respective maintainers;
we are glad to hear about them too, so we can react.
