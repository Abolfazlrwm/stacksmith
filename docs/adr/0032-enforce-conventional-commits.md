# ADR-0032: Enforce Conventional Commits

- **Status:** accepted
- **Date:** 2026-12-16
- **Supersedes**: the implicit commit convention from ADR-0001

## Context

stacksmith reached v1.0.0 with 149 commits. An audit of the history shows
two problems:

1. **No enforcement.** Commits *mostly* follow Conventional Commits
   (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`), but nothing prevents a
   contributor from pushing `WIP stuff` or `updated the deploy`. The
   release-drafter categories (added in v0.7.0, ADR-0026) silently drop
   non-conventional PR titles into no category.

2. **Leftover `fixup!` commits.** 10 `fixup!` commits are still in the
   history of `main` (the Phase 13 rebase errored out on unstaged changes
   and the fixup was force-pushed instead of squashed). They are harmless
   but they pollute the linear history and they are exactly the failure
   mode a pre-push hook should catch.

## Decision

Adopt Conventional Commits 1.0.0 as the project's commit convention, and
enforce it at three layers:

1. **Local hook** (`.githooks/commit-msg`) — runs `commitlint` on the
   message in the editor, so contributors get feedback before they leave
   the terminal. Installed via `git config core.hooksPath .githooks`.

2. **Pre-push hook** (`.githooks/pre-push`) — refuses to push branches
   that contain leftover `fixup!` or `squash!` commits, with a one-line
   remedy printed.

3. **CI gate** (`.github/workflows/commitlint.yml`) — two jobs:
   - `pr-title` uses `amannn/action-semantic-pull-request` to check the
     PR title against the allowed `type(scope?): subject` pattern.
   - `commit-messages` runs `commitlint` over every commit added by the
     PR (from `merge-base` to `head`), so a rebase that drags in old
     commits does not get blamed, and a force-push that rewrites history
     still gets checked.

The config (`commitlint/commitlint.config.cjs`) extends
`@commitlint/config-conventional` and adds:

- `header-max-length: 72` (the GitHub commit list truncates at 72)
- `subject-case: lower-case` (warning — technical identifiers like
  `ADR-0032`, `GHCR`, `cosign`, `v1.0` are naturally mixed-case, so this
  is a nudge, not a block)
- `subject-full-stop: never` (no trailing period)
- `body-max-line-length: 100` (warning, matches our prose wrap)

## Allowed types

| Type     | When to use it                                                |
| -------- | ------------------------------------------------------------- |
| `feat`   | A new user-facing capability or a new script                  |
| `fix`    | A bug fix to existing behavior                                |
| `docs`   | Changes to `docs/`, `README.md`, `CHANGELOG.md`, ADRs         |
| `style`  | Formatting, whitespace, import order — no behavior change     |
| `refactor` | Restructure without behavior change                        |
| `perf`   | A change that improves performance                            |
| `test`   | Adding or fixing tests                                        |
| `build`  | Changes to `Dockerfile`, `Makefile`, dependencies             |
| `ci`     | Changes to `.github/workflows/`                               |
| `chore`  | Releases, version bumps, housekeeping                         |
| `revert` | Reverting a previous commit                                   |

## Scope

The scope is optional. When present it is lowercase and matches the area:
`feat(deploy):`, `fix(ci):`, `docs(adr):`, `feat(ops):`. The
release-drafter categories map to types, not scopes, so scope choice is
free.

## Breaking changes

Two equivalent ways to mark a breaking change:

```
feat(deploy)!: drop Docker 20.x, require 24.x

feat(deploy): drop Docker 20.x, require 24.x

BREAKING CHANGE: Docker 20.x is no longer supported. Upgrade to 24.x
before pulling this release.
```

The `!` form is preferred for short subjects. The `BREAKING CHANGE:`
footer is required when the subject does not fit the reason.

## Consequences

- **Positive:** release-drafter now categorizes 100% of PRs. The
  changelog reads as a clean `feat / fix / docs / ci / chore` breakdown.
- **Positive:** future contributors cannot accidentally push a `WIP`
  commit, because both the local hook and CI refuse it.
- **Positive:** the pre-push hook prevents the fixup!-pollution failure
  mode that hit Phase 13 from recurring.
- **Negative:** the first force-push of a non-conventional branch will
  fail CI. Contributors must rewrite history with `git rebase -i` or
  `git commit --amend`. This is a one-time cost; the local hook makes it
  rare.
- **Negative:** commitlint pulls in Node as a dev dependency. The
  `commitlint/` directory is self-contained (its own `package.json`), so
  the main repo stays Python+Shell. CI installs it on demand.

## Rollout

1. Merge this ADR + config + workflow + hooks (this PR).
2. The 10 leftover `fixup!` commits on `main` are left in place — they
   are historical and rewriting `main`'s published history would break
   every clone. The pre-push hook prevents new ones.
3. Going forward, every PR must pass the `commitlint` workflow.
