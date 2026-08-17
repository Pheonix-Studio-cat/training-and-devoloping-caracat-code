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
