# Contributing to StackSmith

Thank you for your interest in contributing.

This kit is deliberately small and opinionated: one VPS, compose as the
deployment unit, and a hard rule that **a claim in the README must be proven
by a CI job**. A contribution that strengthens that rule (a better drill, a
tighter script, a clearer runbook) is worth more than a new feature.

## Getting Started

Prerequisites: Docker with Compose v2.20 or newer, `make`, and a host you can
break (not the production VPS).

```bash
git clone https://github.com/Abolfazlrwm/stacksmith.git
cd stacksmith
cp .env.example .env   # then fill in the values
make doctor            # host readiness check
make up                # bring the stack up, wait for health
make smoke             # run the local smoke path
```

## Development Workflow

1. Create a branch from `main`:
   `feat/short-slug`, `fix/short-slug`, `docs/short-slug` or `chore/short-slug`.
2. Make the change, with the drill or check that proves it.
3. Run everything CI runs:

   ```bash
   make lint            # yamllint, shellcheck, markdownlint
   ```

   For changes touching `app/`, also run the unit suite locally (this
   is what the `unit` CI job runs):

   ```bash
   # Install only the unit-test dep subset — torch and
   # sentence-transformers are multi-hundred-MB wheels and are
   # lazy imports; the suite exercises the embedding layer through
   # its documented stub provider.
   grep -vE '^(torch|sentence-transformers)==' app/requirements.txt \
     | python -m pip install -r /dev/stdin pytest==8.3.3 markdown
   python -m pytest app/tests -v --tb=short
   ```

   The suite is 112 tests covering ingestion, chunking, citation
   resolution, upload validation, the rate limiter, the version
   plumbing, the LLM adapters, the embedding stub, and the request
   serializers. It runs in under a second and needs no database —
   proving the wiring that ships.

4. Commit with [Conventional Commits](https://www.conventionalcommits.com/).
   The body should say *why*, not restate the diff. See the format rules
   below — CI will reject messages that do not match.
5. Push and open a pull request whose title also follows the format.

## Commit message format

Every commit and every PR title must match:

```text
type(scope): subject

optional body, wrapped at 100 chars

optional footer
```

- **type** is required and must be one of: `feat`, `fix`, `docs`, `style`,
  `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **scope** is optional, lowercase when present (`deploy`, `ci`, `ops`).
- **subject** is imperative mood (`add`, not `added`), no trailing period,
  max 72 chars. Lower-case is preferred but not enforced, so technical
  identifiers (`ADR-0032`, `GHCR`, `cosign`, `v1.0`) stay readable.
- **breaking change**: use the `!` marker (`feat(deploy)!: drop Docker 20.x`)
  or a `BREAKING CHANGE:` footer with an explanation.

Examples:

```text
feat(deploy): cosign verify before switching upstream

deploy.sh now checks for cosign and a GHCR image before starting the
target. If both are present, it verifies the image signature. Graceful
degradation: local builds skip the check.

fix(ci): remove unsupported --yes flag from cosign verify
docs(adr): ADR-0032 enforce conventional commits
chore: v1.0.1 — commit convention enforcement
```

### Local hook (optional but recommended)

Install the local hooks so you get feedback before pushing:

```bash
git config core.hooksPath .githooks        # legacy commit-msg + pre-push
# OR use pre-commit (covers markdownlint + commitlint + shellcheck +
# yamllint in one place):
pip install pre-commit
pre-commit install --install-hooks -t pre-commit -t commit-msg
pre-commit run --all-files                 # run every hook once
```

The `commitlint` config lives in `commitlint/commitlint.config.cjs`; the
pre-commit hooks are defined in `.pre-commit-config.yaml` at the repo
root. Both run the same checks CI runs, so a green local run means a
green CI run on the lint gates.

### Enforcement

The `commitlint` workflow runs on every PR:

| Check                       | Tool                                  | Failure mode |
| --------------------------- | ------------------------------------- | ------------ |
| PR title format             | `amannn/action-semantic-pull-request` | PR fails     |
| Every commit on the branch  | `@commitlint/cli`                     | PR fails     |

If a commit fails the check, reword it with:

```bash
git rebase -i origin/main
# mark the commit `reword`, edit the message, save, quit
git push -f
```

See [ADR-0032](docs/adr/0032-enforce-conventional-commits.md) for the full
rationale and the list of allowed types.

## Branch protection on `main`

`main` is protected. Direct pushes are rejected; every change goes through a
pull request that must satisfy:

| Requirement | Value |
|-------------|-------|
| Required status checks | `unit` (Django app unit tests), `lint`, `smoke`, `restore-drill`, `commitlint` |
| Required approving reviews | 0 — this is a single-maintainer project, and GitHub does not allow self-approval |
| Force pushes | blocked |
| Branch deletion | blocked |
| Conventional commit PR title | required |

The full drill matrix (36 checks at v1.2.2) runs on every PR; the
required checks above are the subset that must be green before merge.
The rest (SBOM, cosign-verify, k6 load tests, loki/tempo readiness,
disaster-recovery drill) are advisory but expected green.

## Script standards

- Bash with `set -euo pipefail`, shellcheck-clean, quoted variables.
- Every script prints what it is doing step by step, so a 03:00 deploy is
  readable in the log.
- Destructive actions (drop, restore, upstream switch) require either an
  interactive confirmation or an explicit `--yes`.

## What a reviewable pull request looks like

- One concern. If the description needs the word "also", split it.
- Evidence, not claims. If the PR says "deploy still works", it points at the
  green drill run that proves it.
- Anything deliberately left undone is written down in
  `docs/known-limitations.md`, so it does not become invisible later.

## Reporting Issues

Use the issue template. Include steps to reproduce, expected versus actual
behaviour, and your version (`v1.2.2` or `main @ <sha>` — the version is
also reported by the `GET /` endpoint of a running stack). Check
`docs/known-limitations.md` first — the behaviour may be a documented
limitation rather than a defect.

For security issues, see [SECURITY.md](SECURITY.md) — do not open a
public issue.

## Code of Conduct

Participation in this community is governed by the
[Contributor Covenant v2.1](CODE_OF_CONDUCT.md). By participating you
agree to uphold its standards. Reports go to
`abolfazlrwm@users.noreply.github.com` and are handled confidentially.
