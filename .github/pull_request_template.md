# Pull request

## What

<!-- One sentence describing what this PR changes. -->

## Why

<!-- One sentence on why this change matters. Link an issue if relevant.
     If the description needs the word "also", split the PR. -->

## Type

<!-- Check one. The PR title's `type(scope):` must match this. -->

- [ ] `feat` — new feature or capability
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only (README, CHANGELOG, ADR, runbooks)
- [ ] `refactor` — code change that neither fixes a bug nor adds a feature
- [ ] `perf` — performance improvement
- [ ] `test` — test-only change
- [ ] `build` / `ci` — build system, CI workflows, dependencies
- [ ] `chore` — maintenance, version bumps
- [ ] `revert`

## Breaking changes

- [ ] No — backward compatible
- [ ] Yes — the PR title uses `feat(scope)!: ...` or has a
      `BREAKING CHANGE:` footer, and the CHANGELOG documents the
      migration

## Checklist

- [ ] Commit messages follow
      [conventional commits](../docs/adr/0032-enforce-conventional-commits.md)
      (`feat:`, `fix:`, `ci:`, `docs:`, `chore:`, scope optional,
      subject ≤ 72 chars)
- [ ] No emojis, no `Co-Authored-By`, no `Generated with` in commit
      messages
- [ ] One logical change per commit — no "and also" commits
- [ ] `yamllint` and `shellcheck` pass locally (`make lint`)
- [ ] If a claim is added to the README, a CI job proves it
- [ ] If a new ADR is added, it has considered-alternatives and
      consequences
- [ ] If a new script is added, it passes `shellcheck` and has
      `set -euo pipefail`
- [ ] If `app/` changed, `python -m pytest app/tests` passes locally

## CI

<!-- Which CI jobs are relevant to this change?
     e.g. lint, unit, smoke, restore-drill, container-scan -->

## Known limitations

<!-- If this PR does not fully close the gap, note it here and in
     docs/known-limitations.md. Delete this section if not applicable. -->
