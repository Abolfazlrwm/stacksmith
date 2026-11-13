# Pull request

## What

<!-- One sentence describing what this PR changes. -->

## Why

<!-- One sentence on why this change matters. Link an issue if relevant. -->

## Checklist

- [ ] Commit messages follow [conventional commits](../docs/conventions.md)
      (`feat:`, `fix:`, `ci:`, `docs:`, `chore:`)
- [ ] No emojis, no `Co-Authored-By`, no `Generated with` in commit messages
- [ ] One logical change per commit — no "and also" commits
- [ ] `yamllint` and `shellcheck` pass locally (`make lint`)
- [ ] If a claim is added to the README, a CI job proves it
- [ ] If a new ADR is added, it has considered-alternatives and consequences
- [ ] If a new script is added, it passes `shellcheck` and has `set -euo pipefail`

## CI

<!-- Which CI jobs are relevant to this change? e.g. lint, smoke, restore-drill -->

## Known limitations

<!-- If this PR does not fully close the gap, note it here and in docs/known-limitations.md -->
