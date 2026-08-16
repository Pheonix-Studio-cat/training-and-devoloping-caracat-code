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

The only secret this project currently uses is `HF_TOKEN`, consumed by
`.github/workflows/sync-to-huggingface.yml` to publish the `hf/` directory to
the Hugging Face model repository. It should be a write-scoped token limited to
that model repository.

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
