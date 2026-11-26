# Maintainers

> The people with merge access to the repository right now.
> Governance and the path to becoming a maintainer are in
> [GOVERNANCE.md](GOVERNANCE.md). Emeritus maintainers are listed at
> the bottom.

## Active

| Name | GitHub | Role | Focus |
| --- | --- | --- | --- |
| Abolfazl Rahimi | [@Abolfazlrwm](https://github.com/Abolfazlrwm) | BDFL / Maintainer | Architecture, security, deploy & ops, app `app/` |

## Responsibilities

A maintainer is expected to, in rough priority order:

1. **Keep `main` green.** If a merge breaks CI or a drill, the
   maintainer who merged it owns the revert or the fix.
2. **Review PRs they did not author** with the same care they'd
   want — read the diff, run the tests locally if the change is
   non-trivial, check the CHANGELOG and ADR implications.
3. **Write ADRs** for decisions that future-them will not be able
   to reverse cheaply. See [adr/INDEX.md](adr/INDEX.md) for the
   log and conventions.
4. **Triage issues** within a week — label, ask for repro, or
   close with a reason. The `labeler` workflow handles PRs; issues
   are manual.
5. **Never push to `main` directly.** Everything is a PR, including
   the maintainer's own work. See [GOVERNANCE.md §4](GOVERNANCE.md).
6. **Respect the release contract.** `VERSION` and `CHANGELOG.md`
   move together; a bump without a CHANGELOG section fails CI.

## Emeritus

_None yet._

Emeritus maintainers have stepped down or been inactive for 6+
months. They keep their commit-history credit and are welcome back
at any time — just open a PR.

## Contact

- **Public:** open a [Discussion](https://github.com/Abolfazlrwm/stacksmith/discussions)
  or an issue.
- **Security:** follow [SECURITY.md](../SECURITY.md) — do **not**
  open a public issue for vulnerabilities.
- **Direct:** `@Abolfazlrwm` on GitHub.

## See also

- [GOVERNANCE.md](GOVERNANCE.md) — how decisions are made
- [CONTRIBUTING.md](../CONTRIBUTING.md) — how to contribute
- [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) — expected behaviour
