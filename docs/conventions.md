# Engineering conventions

How this repository is built. These are working rules, not aspirations: CI
enforces what can be enforced, and the rest is review policy.

## Commits

- Conventional Commits: `feat:`, `fix:`, `docs:`, `ci:`, `chore:`,
  `refactor:`, `test:` - scopes where they help (`feat(compose):`,
  `feat(backup):`).
- Imperative subject, 72 characters or fewer, no noise. The body says why,
  not what the diff already says.
- One logical change per commit. A commit that lands the compose stack and
  rewrites the README is two commits.

## Branches and pull requests

- Branch from `main`: `feat/phase-N-slug` for a phase, `fix/slug`,
  `docs/slug`, `chore/slug` otherwise.
- One phase, one pull request. The merge is a merge commit (no squash), so
  the history keeps the shape of the work.
- CI must be green before merge and stays green after. Direct pushes to
  `main` do not happen.

## Scripts

- Bash with `set -euo pipefail`, shellcheck-clean, quoted variables, no
  silent failures.
- Every script prints what it is doing step by step, so a deploy at 03:00 is
  readable in the log.
- Destructive actions (drop, restore, upstream switch) require either an
  interactive confirmation or an explicit `--yes`.

## Documentation

- ADRs are numbered sequentially and immutable once accepted; a changed
  decision means a new ADR that supersedes the old one.
- Runbooks are living documents; if an incident teaches something, the
  runbook learns it.
- README claims need proof: a feature is done when a CI job exercises it.
  Untested work is listed in Known limitations, not implied.

## Environment and secrets

- `.env.example` documents every variable with a comment and a safe default;
  secrets live only in `.env` (gitignored) on the host.
- No secret, token or private key ever lands in git, logs or a release
  manifest. Manifests fingerprint the environment by variable names, never
  by values.

## Releases

- `VERSION` is the source of truth for the toolkit version; `CHANGELOG.md`
  tracks what changed and what did not.
- Deployment releases are immutable tags: `release-YYYYMMDD-HHMM` plus a
  manifest (git sha, image digests, env fingerprint).
