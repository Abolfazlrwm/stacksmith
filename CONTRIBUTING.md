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
   make lint            # yamllint, shellcheck
   ```

4. Commit with [Conventional Commits](https://www.conventionalcommits.org/).
   The body should say *why*, not restate the diff.
5. Push and open a pull request.

## Branch protection on `main`

`main` is protected. Direct pushes are rejected; every change goes through a
pull request that must satisfy:

| Requirement | Value |
|-------------|-------|
| Required status checks | `lint`, `smoke`, `restore-drill` |
| Required approving reviews | 0 — this is a single-maintainer project, and GitHub does not allow self-approval |
| Force pushes | blocked |
| Branch deletion | blocked |

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
behaviour, and your version (`v0.1.0` or `main @ <sha>`). Check
`docs/known-limitations.md` first — the behaviour may be a documented
limitation rather than a defect.

## Security Issues

Do not open a public issue for a security vulnerability. See
[SECURITY.md](SECURITY.md).
