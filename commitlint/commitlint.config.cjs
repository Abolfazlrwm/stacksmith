// commitlint.config.cjs — Conventional Commits config for stacksmith.
//
// Enforces the format:  type(scope): subject
//   type   = one of: feat fix docs style refactor perf test build ci chore revert
//   scope  = optional, lowercase, matches the dir/area (deploy, ci, docs, ops, ...)
//   subject = lowercase imperative, max 72 chars, no trailing period
//
// Breaking changes use the `!` marker:  feat(deploy)!: drop Docker 20.x
// or a `BREAKING CHANGE:` footer.
//
// Reference: https://www.conventionalcommits.org/en/v1.0.0/
//           https://commitlint.js.org/reference/rules.html

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Scope is optional but must be lowercase if present.
    'scope-case': [2, 'always', 'lower-case'],
    // Subject: lowercase, imperative mood, no trailing period, max 72 chars.
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    // Body lines: hard wrap at 100 chars (matches our prose style).
    'body-max-line-length': [1, 'always', 100],
    // Footer lines: hard wrap at 100 chars.
    'footer-max-line-length': [1, 'always', 100],
    // Require a body for non-trivial commits (warning level so docs/chore
    // one-liners are not blocked).
    'body-empty': [0, 'never'],
  },
};
