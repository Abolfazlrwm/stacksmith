# Governance

> **Status:** Active. Last revised 2026-11-25 (v1.2.7).
>
> This document defines how decisions are made in StackSmith, who
> makes them, and how a contributor becomes a maintainer. It is short
> on purpose: the bar is *honest and useful*, not *elaborate*.

## 1. Project status

StackSmith is **single-maintainer, open to contributors**. It is not
a foundation project, not a CNCF sandbox, and not seeking one. The
governance model below is the smallest one that fits a project of
this shape and that does not lie about its maturity.

| Dimension | Current state |
| --- | --- |
| Maintainers | 1 ([@Abolfazlrwm](https://github.com/Abolfazlrwm)) |
| Active since | 2026-11-03 |
| Release cadence | Patch/minor every 1–2 weeks; no fixed schedule |
| Stability promise | `app/` product API is stable since v1.0.0 (ADR-0031); the deployment kit (`docker-compose*.yml`, `deploy/`, `scripts/`) is stable since v1.2.0 |
| Breaking changes | Never on `main`. Always behind a deprecation cycle in a minor release, removed in the next major (none planned). |

## 2. Roles

### Contributor

Anyone who opens a merged PR or answers issues usefully. No formal
permission beyond what the default GitHub flow gives.

### Maintainer

Has push access to the repo and the right to merge PRs. A maintainer
is expected to:

- review PRs they did not author with the same care they'd want,
- keep `main` green — if a merge breaks CI or a drill, the
  maintainer who merged it owns the revert or the fix,
- write ADRs for decisions that future-them will not be able to
  reverse cheaply (see [adr/INDEX.md](adr/INDEX.md)),
- never push to `main` directly. Everything goes through a PR,
  including the maintainer's own work (see §4).

### BDFL

Until a second maintainer is added, the founding maintainer
([@Abolfazlrwm](https://github.com/Abolfazlrwm)) is the BDFL — the
tie-breaker when there is no consensus and the person accountable
for the security and availability of the project. The role is
intended to be **ceremonial**, not dictatorial: in practice almost
every decision should be reversible and made by whoever is doing
the work.

## 3. How decisions are made

| Decision type | Made by | Where |
| --- | --- | --- |
| Bug fix, refactor, doc edit | The contributor + one reviewer | PR |
| New feature in `app/` | Maintainer sign-off + an ADR | PR + `docs/adr/` |
| Change to a deployment contract (`docker-compose*.yml`, env vars, Makefile targets) | Maintainer sign-off + an ADR | PR + `docs/adr/` |
| Dependency major bump | Maintainer sign-off | PR (label `breaking`) |
| Security fix | Maintainer, privately first | See [SECURITY.md](../SECURITY.md) |
| Changing this document | Maintainer + 7-day call for objections | Issue |

The default is **lazy consensus**: if you propose a change in a PR
or issue and nobody objects in a reasonable window (3 days for a
patch, 7 days for a feature), it proceeds. Objecting means
commenting with a reason and a counter-proposal, not just a -1.

## 4. Branch and merge policy

- `main` is **always deployable**. The Pages site, the Release
  artifacts, and the demo all read from `main`.
- No direct pushes to `main`, including by maintainers. Every change
  is a PR. The `labeler` and `commitlint` workflows enforce this.
- PRs are squash-merged with a conventional-commit title
  (`feat:`, `fix:`, `docs:`, `chore:`, `build:`, `refactor:`). The
  body is the PR description.
- Branch protection requires: green CI on the required checks, at
  least one review (maintainers can self-review only for hotfixes to
  `main`, logged in the PR), and `delete_branch_on_merge` is on.
- Hotfixes to a released version go on `main` and are cherry-picked
  to a `release/vX.Y` branch if one exists. We do not maintain
  long-lived release branches otherwise.

## 5. How to become a maintainer

There is no application form. The path is:

1. Contribute consistently for ~2 months — reviews, fixes, drills.
   Quality matters more than count.
2. The existing maintainer(s) propose adding you in a GitHub
   Discussion. 7-day call for objections.
3. If no objection, you get push access and are listed in
   [MAINTAINERS.md](MAINTAINERS.md).

A maintainer can step down to contributor at any time by asking;
no reason required. Inactive maintainers (no commits, reviews, or
issue replies for 6 months) are moved to *Emeritus* in
MAINTAINERS.md but keep their commit history credit.

## 6. Conflict resolution

Disagreements stay technical. If two maintainers disagree and
can't reach consensus in 72 hours, the BDFL decides and writes a
short rationale in the PR. If a contributor disagrees with a
maintainer's decision, the venue is a GitHub Discussion, not the PR
thread. The CoC applies everywhere; see
[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

## 7. Changes to this document

This governance is itself versioned. Material changes go through a
PR with the `docs` label and a 7-day call for objections posted as
a Discussion. Typos and clarifications can be merged directly.

## See also

- [MAINTAINERS.md](MAINTAINERS.md) — who has merge access right now
- [CONTRIBUTING.md](../CONTRIBUTING.md) — how to make a contribution
- [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) — expected behaviour
- [SECURITY.md](../SECURITY.md) — how to report a vulnerability
- [adr/INDEX.md](adr/INDEX.md) — the architectural decision log
