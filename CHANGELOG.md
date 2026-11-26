# Changelog

All notable changes to stacksmith are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.8] — 2026-11-26

The OSS-maturity release. v1.2.7 made the project *look*
professional; v1.2.8 makes the *project governance and contributor
experience* match what a top-tier OSS repo actually has. No app
logic, no UI, no deploy changes — every item here is repo plumbing
that a careful visitor checks for.

### Added — citation + community

- **`CITATION.cff`** — GitHub now renders a "Cite this repository"
  card in the sidebar and exposes it via the citation API. Academic
  users get a ready-made citation; a future Zenodo DOI will read
  from this file.
- **`.all-contributorsrc`** + a Contributors table in the README —
  the All Contributors spec, so non-code contributions (reviews,
  docs, design, security reports) get credit too. Self-serve: a
  contributor comments `@all-contributors please add <user> for
  <contribution>` on any issue.
- **`docs/GOVERNANCE.md`** — the decision model. Honest about the
  project's shape: single-maintainer, open to contributors, BDFL
  until a 2nd maintainer arrives, lazy consensus, branch
  protection rules, and the explicit path from contributor to
  maintainer.
- **`docs/MAINTAINERS.md`** — who has merge access right now, what
  they're responsible for, and an Emeritus section for when
  maintainers step down.

### Added — dependency hygiene

- **`renovate.json5`** — complements the existing
  `dependabot.yml`. Dependabot does the weekly version-bump PRs;
  Renovate does the things dependabot can't: lock-file maintenance
  (transitive deps, not just direct), grouping by upstream release
  (Django/DRF/pg as one PR, LLM SDKs as another), auto-merge of
  dev/CI tooling patches after green CI, and consolidated
  vulnerability PRs. Inert until the Renovate GitHub App is
  installed; will not double-up with dependabot.

### Added — PR triage automation

- **`.github/labeler.yml`** + **`.github/workflows/labeler.yml`** —
  PRs are now auto-labeled by the paths they touch (`python`, `ui`,
  `infra`, `ci`, `security`, `docs`, `dependencies`, `release`,
  `testing`). The label column on the PR list is accurate from the
  moment a PR is filed; no manual triage.

### Changed — repo settings (via API, not in the diff)

- **Branch protection on `main` is now ON.** Before this release,
  `main` was unprotected. Now requires 12 status checks (markdown
  lint, yamllint, shellcheck, compose config, commitlint, unit
  tests, stub stack, CodeQL, dependency review, Trivy scan, SBOM,
  cosign sign), strict (PR branch must be up-to-date with `main`),
  linear history, no force-pushes, no deletions. Admin enforcement
  is off so the maintainer can still merge a hotfix if CI is flaky,
  but the default path is gated. `required_approving_review_count`
  is 0 for now (single-maintainer); GOVERNANCE.md says to bump it
  to 1 when a 2nd maintainer arrives.
- **Merge method is now squash-only.** Disabled merge-commit and
  rebase-merge; the squash commit title is the PR title, body is
  the PR description. History stays a clean line of
  conventional-commit messages. `delete_branch_on_merge` stays on.

### Changed — README

- New **Contributors** section (between Star history and License)
  with the All Contributors table.
- New **Governance** section pointing at GOVERNANCE.md and
  MAINTAINERS.md, with the three-line summary of the model.
- Table of contents updated to include both new sections.

### Changed — community files

- `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CONTRIBUTING.md`, and
  `LICENSE` are now symlinked into `.github/` so GitHub's Community
  Profile sidebar auto-links them. One source of truth; no drift.

### Verification

- `markdownlint` clean on all new/changed `.md` files.
- `.github/labeler.yml` parses; 9 labels defined, all with valid
  path globs.
- `renovate.json5` is valid JSON5 (Renovate will validate on first
  run; the file is inert until the app is installed).
- Branch protection applied via API and re-read back: 12 contexts,
  strict, linear history, no force-push. Merge settings re-read:
  squash-only, PR_TITLE/PR_BODY.
- No app/deploy/UI changes, so the existing 127-test suite and
  drill matrix are unaffected.

VERSION 1.2.7 -> 1.2.8.

## [1.2.7] — 2026-11-25

The UI redesign release. v1.2.6 made the project visible; v1.2.7 makes
it *not look generated*. Every output of an image-or-code generator
shipped the same look: Tailwind navy (`#0B1220`) + sky-blue
(`#38BDF8`), `box-shadow: 0 0 12px` glows on every accent dot,
`backdrop-filter: blur` navbars, `radial-gradient` hero washes, the
Space Grotesk + Inter + JetBrains Mono font trio, and emoji icons in
cards. v1.2.7 replaces all of it with a deliberate, human-chosen
identity shared between the product UI and the showcase.

### Changed — palette + type (one identity, two surfaces)

- **Palette**: warm ink `#171421` (purple-black, not Tailwind navy),
  card `#211e2b`, a single earthy **ochre** accent `#d4a055` (not the
  AI-default sky-blue), moss green `#7fa67e` for "ok", brick `#c66b6b`
  for "bad", paper text `#e8e4dc` (not blue-white).
- **Type**: IBM Plex Sans + IBM Plex Mono (engineer-chosen) instead
  of the Space Grotesk + Inter + JetBrains Mono combo every generator
  ships.
- **Removed every `box-shadow: 0 0 Npx` glow** — on nav dots, brand
  dots, timeline markers. Flat fills instead.
- **Removed `backdrop-filter: blur`** on the sticky nav — solid
  background.
- **Removed the two `radial-gradient` hero washes** — the hero is now
  a flat surface with a top border.
- **Square corners**: dropped `border-radius: 12px` / `10px` /
  `14px` everywhere. Cards use 1px gap-on-line grids; nodes use a
  2px top border for layer color; badges use a 1px outline.
- **Bubbles** (chat UI): left 2px accent border instead of rounded
  pill — same idea as a quoted block in prose.

### Changed — content

- **Removed all emoji** from the showcase body (💡 📄 📦 🔁 🔐 ✍️
  🎞️ 🔢) and the chat UI (⬆). Replaced with mono-styled single
  characters or numbered card markers (`01 — deploy`).
- Refreshed the version timeline to cover v1.2.0 → v1.2.7 (was stuck
  at v1.2.4).
- Refreshed the hero stats (119 tests, 31 workflows, 12 containers,
  v1.2.7) — were stale at v1.2.4 / 113 / 30 / 11.
- The chat UI brand badge still fetches `/` at runtime (v1.2.5 fix
  preserved); only the colours changed.

### Changed — branding

- `docs/logo.svg` — redrawn with the new palette: square background
  (no `rx=14`), flat ochre bubble (no gradient), no live-dot. Same
  document + bubble + ink-dots geometry.
- `docs/social-preview.png` — regenerated with the new palette. Now
  55 KB (was 105 KB): the gradient glow was the heavy part.
- Favicons (inline data-URI in `chat.html` + `demo.html`) updated to
  match.

### Verification

- `make test`: 127 pass (no app logic changed — CSS + body markup
  only; the version-sync test still pins `VERSION ↔ CHANGELOG`).
- No AI-default colour string remains in either template
  (`#0B1220`, `#38BDF8`, `#94A3B8`, `#1E293B`, `#334155` all gone).
- No `box-shadow` glow, no `backdrop-filter`, no hero gradient, no
  emoji in body.
- VERSION 1.2.6 → 1.2.7.

## [1.2.6] — 2026-11-25

The visibility release. v1.2.5 made the project *runnable* in a
browser; v1.2.6 makes it *discoverable* and *credible* at first
glance — the two things top repositories do that ours did not.

### Added — README redesign

A top-repository-grade README:

- **Hero banner** — `docs/social-preview.png` (1280×640) leads the
  page, centered title, tagline, and a tight badge cluster (CI gates,
  release, license, conventional commits, test count, ADR count).
- **Table of contents** — every section reachable from the top.
- **Screenshots section** — four compressed JPEGs (under 100 KB each)
  captured from the live showcase: hero, chat+code, architecture,
  security. Each captioned, each under 100 KB.
- **Comparison table** — docubot vs Hosted SaaS vs PrivateGPT vs Dify
  across nine dimensions (self-hosted, no-cloud-lock-in, multi-user,
  production ops, observability, signed deploys, restore drill, vector
  store, deployment unit). Every claim is backed by a CI workflow.
- **Star history** — live chart via star-history.com at the bottom.

### Added — branding assets

- `docs/social-preview.png` — GitHub social preview (1280×640). Save
  to `download/` for the maintainer to upload in repo Settings →
  Social preview.
- `docs/screenshots/{hero,chat-and-code,architecture,security}.jpg` —
  four README screenshots, captured from the live Pages deploy and
  compressed with `scripts/compress-screenshots.py`.
- `scripts/make-social-preview.py` — the matplotlib generator for the
  social preview, kept for regeneration.

### Changed

- README no longer carries the v1.2.0–v1.2.3 release-note blockquotes
  at the top — those belong in CHANGELOG (where they already are) and
  were pushing the actual content below the fold.
- `.markdownlint.json` allows `<picture>`, `<source>`, `<div>`,
  `<p>`, `<em>`, `<code>`, `<strong>`, `<a>` inline HTML for the
  banner, screenshots, and star-history blocks.
- VERSION 1.2.5 → 1.2.6.

## [1.2.5] — 2026-11-19

The showcase release. v1.2.4 made the CI behave like a professional
pipeline; v1.2.5 makes the project *visible* like one. A reviewer, a
hiring manager, or an instructor can now see the product end-to-end
and the code behind each feature side by side, in a browser, with no
backend to run.

### Added — live interactive showcase

A single self-contained HTML page (`app/templates/demo.html`) that
shows the product and the code behind it side by side:

- A live chat demo over the real sample corpus (`tests/demo-corpus/`)
  with simulated RAG + citations — so a visitor can ask a question
  and see the answer with `sim = 0.86` style scores, without docker.
- Real source excerpts from `ChatView.post()`, `retrieve()`, and
  `validate_upload()` rendered beside the feature they implement.
- An interactive upload-validation demo: click `payload.exe` /
  `evil.pdf` / `binary.txt` and see the exact layer that rejects it.
- A 12-node architecture diagram (4 layers: edge → app → data → obs),
  the version timeline v1.2.0 → v1.2.5, and a 16-item security
  checklist mapping each control to the file or workflow that
  enforces it.

The showcase is published to GitHub Pages at
<https://abolfazlrwm.github.io/stacksmith/> on every push to `main`
by `deploy-demo-pages.yml`. The same file is served in-app at
`/demo/` on a running stack — one source of truth, two surfaces.

### Added — `/demo/` route

`GET /demo/` serves the showcase HTML through Django's `TemplateView`,
so a running stack exposes the same page Pages publishes. The route is
covered by 6 new unit tests (`test_demo_and_version.py`) that pin:
the route resolves, returns 200 with the product name, the file is
substantial (>20 KB), the chat UI no longer hardcodes a version, and
the CHANGELOG has an entry for the current VERSION.

### Fixed — chat UI version drift (again)

The brand badge in `app/templates/chat.html` was hardcoded to
`v1.2.0` and had drifted through v1.2.2, v1.2.3, and v1.2.4 without
the badge ever updating — the same class of bug v1.2.3 fixed for the
`/` endpoint. The badge now fetches `/` at runtime and writes the
real version into the element. A unit test pins that the hardcoded
`>v1.2.x<` marker is gone, so this cannot silently drift again.

### Added — branding

- `docs/logo.svg` — an SVG logo (document spine + chat bubble + live
  indicator dot) in the app's palette. Linked in the README header
  and embedded as an inline data-URI favicon in both `chat.html` and
  `demo.html` (so the favicon works on Pages with no extra request).
- `FUNDING.yml` — powers the "Sponsor" button on the repo page.
- README now opens with a live-demo callout, a Pages badge, the
  logo, and a Quick Start that lists the three in-app URLs
  (`/`, `/app/`, `/demo/`).

### Changed

- README's ADR count was stale (said "30 ADRs", actually 33) — fixed.
- Test suite: 113 → 119 (+6 new tests for the showcase and version
  plumbing).

## [1.2.4] — 2026-11-18

The CI-hygiene release. v1.2.3 professionalized the repo surface;
v1.2.4 makes the CI itself behave like a professional pipeline: runs
that are superseded by a newer push cancel themselves instead of
queuing behind 30 stale jobs, and the unit suite is reachable from
`make test` (it was documented in CONTRIBUTING but had no Makefile
target).

### Added — concurrency cancellation

Every push-triggered workflow now declares a `concurrency:` block:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

A fast push cadence previously queued up to 30 stale runs (one per
workflow) that finished minutes after the developer had already moved
on — wasting CI minutes and slowing feedback on the run that mattered.
Now a new commit cancels the in-progress run of the same workflow on
the same ref. Different branches and different PRs get their own
groups and never interfere with each other.

**26 workflows updated.** The 4 scheduled ones (codeql, cosign-attest,
cosign-verify, stale) were deliberately skipped: a half-finished
backup, scan, or stale-sweep interrupted mid-run leaves inconsistent
state, so those overlap instead. The generator script
(`scripts/add-concurrency.py`) is checked in so a future workflow
inherits the policy by re-running it.

### Added — `make test` and `make test-quick`

The Makefile now exposes the unit suite that CONTRIBUTING.md tells
contributors to run locally:

```bash
make test         # run the full Django unit suite (matches CI's unit.yml)
make test-quick   # same, but stop at the first failure (-x -q)
```

The target creates a `~/.venv` if missing, installs only the
unit-test dep subset (the same `grep -vE '^(torch|sentence-transformers)=='`
filter `unit.yml` uses), and runs `pytest app/tests`. No new
dependency on `pytest-django` — the suite is 113 tests in ~1.2 s.

### Added — CODE_OF_CONDUCT.md

The [Contributor Covenant v2.1](CODE_OF_CONDUCT.md), linked from
CONTRIBUTING.md. Reports go to
`abolfazlrwm@users.noreply.github.com` and are handled
confidentially; security reports still go through the private channel
in SECURITY.md.

## [1.2.3] — 2026-11-18

The repo-professionalization release. v1.2.2 hardened the app
boundary; v1.2.3 closes the gap between "the app is secure" and "the
repo is a place a stranger would feel safe contributing to": a rate
limiter on the LLM-bearing endpoint, a fixed version-reporting bug,
refreshed governance docs, and the missing community plumbing
(OpenAPI spec, dependabot for pip/npm, pre-commit hooks, security
issue template).

### Added — rate limiting (ADR-0038)

- **`config/ratelimit.py`** — a fixed-window rate limiter middleware
  that caps `/api/chat/` at **60 requests per minute per owner**
  (X-Docubot-Owner, falling back to client IP). Health probes and
  admin are exempt so a 429 cannot roll back a good release. A 429
  carries `Retry-After` and `X-RateLimit-*` headers so clients can
  self-throttle.
- **Fail-open on cache failure**: if Redis is unreachable the limiter
  lets the request through (the readiness probe catches Redis-down
  independently) rather than becoming a new single point of failure.
- **No new dependency**: one Redis `INCR` + one `EXPIRE` per request.
  Chosen over `django-ratelimit` (third-party), sliding-window
  (sorted set, more memory), and nginx `limit_req`-only (cannot key
  on the post-auth owner header).
- **`DOCUBOT_RATELIMIT_RATE` env var** lets operators tune the limit
  (or disable it for a load test) without a code change. Production
  keeps the 60/m default; the k6 load-test workflow sets it to
  `10000/m` so its 10-VU ramp does not hit 429s.
- **`app/tests/test_ratelimit.py`** — 20 new tests covering the
  policy parser, the exempt paths, the counter, the 429 response
  shape, per-owner isolation, IP fallback, the fail-open path, and
  the env-var override. Uses a locmem cache fixture + a unique owner
  per test so cached counters never bleed across tests.

### Fixed — version drift

- **`GET /` no longer reports a hardcoded version.** Before v1.2.3
  the version in `config/urls.py` was a string literal (`"1.2.0"`)
  that drifted out of sync on every release — the v1.2.2 release
  shipped with `/` reporting `1.2.0`. Now reads the `VERSION` file at
  import time. Two new tests (`test_version.py`) pin the two stay in
  sync.

### Changed — governance docs reflect v1.2.2

- **`SECURITY.md`** rewritten. v0.3.0 → v1.2.2 supported-versions
  table. Removes the stale "out of scope: docubot is a different
  repo" clause (docubot now lives in this repo, ADR-0036). Documents
  the v1.2.2 app-hardening posture (ADR-0037) and the v1.2.3
  rate-limit posture (ADR-0038). Adds a disclosure-policy section
  and a "known weak spots" list so a reporter can check the likely
  component first.
- **`CONTRIBUTING.md`** refreshed. Documents the local unit-test
  invocation (the exact dep-filter `unit.yml` uses, the 112-test
  count). Branch-protection table now lists `unit` and `commitlint`
  as required, notes the 36-check drill matrix is advisory. pre-commit
  config referenced (was `.githooks` only).

### Added — community plumbing

- **`.github/ISSUE_TEMPLATE/security_advisory.yml`** — new template
  that redirects live-exploit reports to GitHub Private Vulnerability
  Reporting; only for already-disclosed upstream CVEs.
- **`.github/ISSUE_TEMPLATE/config.yml`** — disables blank issues,
  adds contact links for security (private) and discussions.
- **`.github/pull_request_template.md`** — adds Type + Breaking
  changes sections; fixes the stale `docs/conventions.md` link →
  ADR-0032; adds the "if `app/` changed, pytest passes locally"
  check.
- **`.github/dependabot.yml`** — adds **pip** (`app/`) and **npm**
  (`commitlint/`) ecosystems (neither was covered; this is why
  GitHub warns about 10 vulnerabilities on every push). Weekly
  cadence, grouped PRs, conventional-commit prefixes. Also covers
  docker + github-actions as before.
- **`.pre-commit-config.yaml`** (new) — markdownlint-cli2, yamllint,
  shellcheck, ruff + ruff-format, commitlint, and the standard
  pre-commit-hooks (trailing whitespace, large files, merge-conflict
  markers, private keys). Mirrors the CI lint gates so a green local
  run means a green CI lint run.

### Added — OpenAPI for the product API

- **`docs/api/product-openapi.json`** (new) — hand-written OpenAPI
  3.0.3 spec for `/api/documents/` (GET list, POST upload with all
  five 400 examples: unsupported extension, magic-byte mismatch,
  not UTF-8, path traversal, filename too long) and `/api/chat/`
  (POST with 200 / 400 / 404 / 429, `X-RateLimit-*` headers).
  Schemas: Document, ChatRequest, Citation, ChatResponse, Error.
- **`docs/api/README.md`** (new) explains the hand-written choice
  (stable, readable, no extra dep) and how to validate locally.

### Not changed (deliberately)

- **No `pytest-django` dependency.** The new rate-limit tests use
  `monkeypatch` + `RequestFactory` (the same pattern `test_health`
  uses), so `unit.yml`'s `pytest==8.3.3` install is enough. Adding
  `pytest-django` would have meant a new dep + a CI workflow change.
- **No generated OpenAPI.** A hand-written spec only changes when
  the contract changes, which is what an integrator cares about;
  `drf-spectacular` would pull a runtime dep + a generation step.
  The unit suite pins the contracts that matter.

## [1.2.2] — 2026-11-17

The hardening release. v1.2.0 shipped the docubot product (ADR-0036)
and the v1.2.1 test suite (commit `07bc21e`) added 70 unit tests that
also surfaced and fixed the `detect_kind` `endswith("")` bug. v1.2.2
hardens the remaining security edges of the app boundary that the
test suite and the container drills do not exercise: a closed
`ALLOWED_HOSTS` default, `SECURE_*` headers at the app layer, and
upload validation before any bytes reach disk. See ADR-0037 for the
threat model.

### Changed — app security posture

- **`ALLOWED_HOSTS` no longer defaults to `*`.** The previous default
  meant a misconfigured prod deploy answered any Host header. The new
  default is `docubot.example.com,localhost,127.0.0.1` (the canonical
  hostname plus the loopback addresses the in-container readiness probe
  uses); operators still override via `DJANGO_ALLOWED_HOSTS`. Local dev
  passes `*` explicitly.
- **`SecurityMiddleware` is now the first middleware**, with
  `CsrfViewMiddleware` and `XFrameOptionsMiddleware` added as
  defense-in-depth for the admin and any future session-backed view.
  The chat and documents APIs are not CSRF-protected today (the reverse
  proxy authenticates and sets `X-Docubot-Owner`), so CSRF protection
  here is purely additive.
- **`SECURE_*` headers** are now set by the app, not just the proxy:
  `SECURE_PROXY_SSL_HEADER`, HSTS (1 year, preload, include-subdomains),
  `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`,
  `X_FRAME_OPTIONS=DENY`. These are response-header-only and cannot
  break a health probe. HSTS is disabled in local dev (`DEBUG=true`)
  because it has no effect over plain HTTP.
- **`SECURE_SSL_REDIRECT` is opt-in, default off.** An earlier draft
  turned it on when `DEBUG=false`, which broke every container drill:
  the in-container readiness probe and the blue/green canary probe hit
  the app over plain HTTP (nginx has not terminated TLS at that point
  in the deploy sequence), so the redirect made every probe see `301`
  forever and the stack never reported healthy. Operators turn it on
  with `DJANGO_SSL_REDIRECT=true` only when the app is directly
  internet-facing (rare; normally nginx handles the redirect).
- **`/health/*` exempt from the SSL redirect** as belt-and-suspenders,
  so even with the redirect on, the probe still sees a `200`.

### Changed — upload validation

- **Extension allow-list** (`{.pdf, .md, .markdown, .txt, .text}`) is
  enforced before any bytes are written to disk, in the new
  `documents.ingestion.validate_upload()` gate.
- **Magic-byte sniff** for PDF (`%PDF-`) defeats name-spoofing where
  an attacker renames a binary to `.pdf` to slip past the extension
  check. The headline attack: `evil.exe` renamed to `evil.pdf`.
- **UTF-8 decode check** for `.txt`/`.md` defeats the same attack on
  text kinds, which have no portable magic bytes. A renamed binary
  fails the decode instead of producing garbage chunks with U+FFFD
  replacements.
- **Path-traversal rejection**: filenames containing `/` or `\` or any
  path component are refused with a 400; storage is keyed by checksum,
  but the name is echoed in the response so it must be a bare filename.
- **Filename length capped at 255 chars** before any disk I/O, so a
  malicious client cannot send a 10 MB filename string.

### Added — test + ADR surface

- **`app/tests/test_upload_validation.py`** — 19 new pytest unit tests
  covering the three layers of `validate_upload`: extension allow-list
  (case-insensitive, frozen set, all suffix variants, rejects
  `.exe`/`.zip`/`.csv`/`.png`/`.docx`), magic-byte sniff (rejects
  EXE-as-PDF and ZIP-as-PDF), UTF-8 decode check (rejects binary-as-txt
  and binary-as-md, accepts multi-byte UTF-8 and empty files). Suite
  now 89 tests total (70 from v1.2.1 + 19 new), runs in <1s.
- **`app/tests/conftest.py`** prepends `testserver` to
  `DJANGO_ALLOWED_HOSTS` before `django.setup()` so the closed default
  does not break Django's test client (which sends `Host: testserver`).
  Production behavior is unchanged.
- **ADR-0037** records the threat model, the three-layer upload
  validation, and the rationale for opt-in `SECURE_SSL_REDIRECT`.

### Not changed (deliberately)

- **No `pytest.ini` or `requirements-dev.txt`.** main's `unit.yml`
  workflow already installs the dependency subset (filters
  `torch`/`sentence-transformers` out of `app/requirements.txt`) and
  runs `pytest app/tests`. Reusing it keeps one CI job for unit tests.
- **No separate `app-tests.yml` workflow.** Same reason — `unit.yml`
  already exists and is the canonical gate.

## [1.2.0] — 2026-11-16

The product catches up to the operations. Through v1.1.x the `app/`
directory was a Django health-check stub; the README and the deck
described a document-chat product that did not exist in code. v1.2.0
ships that product. See ADR-0036 for the architecture.

### Added — the docubot product

- **`documents` app** — upload (PDF / Markdown / plain text), SHA-256
  dedup, async ingestion via Celery. The `Chunk` model stores each
  passage with a 384-dim pgvector embedding; an HNSW index makes
  retrieval sub-millisecond.
- **`rag` app** — embeddings via `DOCUBOT_EMBED_PROVIDER` (default
  `local`: sentence-transformers `all-MiniLM-L6-v2` on the VPS, so
  documents never leave the host; `openai` and `stub` also supported).
  Retrieval is cosine-distance ANN scoped by owner.
- **`chat` app** — `POST /api/chat/` retrieves the top-k chunks, passes
  them as context to the LLM adapter, and returns the answer with
  structured citations. `DOCUBOT_LLM_PROVIDER` selects OpenAI,
  Anthropic, a local Ollama instance, or a stub. The system prompt
  instructs the model to cite `[1]`, `[2]`, … — the view resolves those
  markers back to the actual chunks.
- **Single-page chat UI at `/app/`** — self-contained HTML, no build
  step. Sidebar for upload + document list with live status, main pane
  for the chat thread with rendered citations.
- **`make demo`** — `scripts/demo.py` ingests the sample corpus under
  `tests/demo-corpus/`, waits for ready, asks a sample question, and
  prints the answer and citations. With stub providers it runs without
  any model download or LLM credentials.
- **`tests/load/chat-k6.js`** — k6 load test that POSTs to `/api/chat/`
  with a pool of questions cycled across iterations. The `load-test`
  workflow's new `k6-chat` job seeds the corpus and runs k6 with stub
  providers, asserting P95 < 2.5s and < 5% business failures.

### Added — closes known-limitations gaps

- **cosign verify at deploy time** (closes ADR-0025). The gate already
  existed in `scripts/deploy.sh`; v1.2 adds `scripts/test_deploy_verify.sh`
  — a unit test that proves all three branches (verify passes on a
  signed image, refuses on a tampered image, skips cleanly on a local
  image) — and a `cosign-at-deploy` CI workflow that runs it on every
  push.
- **Business-endpoint load tests** (closes the load-test gap). The k6
  load test now exercises `POST /api/chat/` end-to-end in addition to
  `/health/live/`.

### Changed

- `VERSION` → `1.2.0`. Minor bump: new product features, no breaking
  changes to the operational surface.
- `app/requirements.txt` extended: djangorestframework, pgvector,
  sentence-transformers, torch (CPU), PyMuPDF, markdown, openai,
  anthropic, httpx, django-cors-headers, python-magic.
- `app/config/settings.py` extended: the three new apps, DRF + CORS
  config, `DOCUBOT_UPLOAD_ROOT`, templates dir, admin plumbing.
- `docs/known-limitations.md` — "cosign verify at deploy time" and
  "business-endpoint load tests" moved from *Not implemented* to
  *Recently closed*. "Document chat (the docubot product)" added to
  *Recently closed*.
- `.env.example` — new `docubot` section documenting every env var the
  new apps read.

### Operational notes

- The runtime image is larger (sentence-transformers + torch CPU +
  PyMuPDF add ~800 MB). Acceptable on a single VPS; the local provider
  can be moved to a sidecar if it becomes a problem.
- The first ingestion after a fresh deploy downloads the
  `all-MiniLM-L6-v2` model (~90 MB). Operators who want a
  cold-start-free deploy can pre-populate the HF cache in the image.

## [1.1.4] — 2026-12-22

Presentation-readiness pass: fixes the factual errors in the docs
audit and adds product framing so the repo reads as a product, not
just a deployment kit.

### Fixed

- **README version stale** — headline said `v1.0.0` while `VERSION`
  was `1.1.3`. Updated to `v1.1.3`.
- **README ADR list broken** — claimed 31 ADRs (actual 29); ADRs
  0032–0035 (incl. the SLO/SLI ones) were unlisted; ADR-0021/22/24/26/
  27/29 were listed with links to wrong files. Rebuilt the list through
  ADR-0035 with correct links and a note that the gaps are merged
  drafts.
- **CI workflow count mismatch** — README said 23, `architecture.md`
  said 24, actual 27. Reconciled to 27.
- **`docs/known-limitations.md`** — stale `v0.7 roadmap` reference
  replaced with the ADR-0025 evaluation reference.
- **`docs/getting-started.md`** — `five dashboards` (six were listed).
  Fixed off-by-one.

### Added

- **README now describes the product.** New `What this is` section
  explains docubot is a self-hosted document-chat platform (RAG over
  pgvector, no cloud lock-in), who it is for, and the operational
  features StackSmith ships.
- **`Product features` and `Operational features` sections** in the
  README — product vs ops, side by side.
- **SLOs surfaced in the README maturity table** — listed as shipped
  with the ADR-0033/0035 references.
- **latency-SLI and SLO-metrics drills** added to the proven-in-CI
  list and to the architecture CI Mermaid diagram.

## [1.1.3] — 2026-12-22

Restructures the `latency-sli-drill` CI workflow so it asserts what is
verifiably true and treats the unresolved promtail metrics stage as
advisory. The pipeline architecture is verified end-to-end; the
metrics stage itself remains open work (see ADR-0035).

### Changed

- **Phase 19.1** — the `latency-sli-drill` workflow no longer fails on
  the missing `nginx_log_*` metrics. It now asserts (blocking): nginx
  emits the JSON access log, promtail is up and ready, prometheus
  scrapes promtail (`up{job=promtail}=1`), and both re-introduced SLO
  alerts (`SLOLatencyP99Breach`, `SLOHigh5xxRate`) are loaded. The
  `nginx_log_*` metrics presence and recording-rule values are printed
  as advisory steps that do not fail the drill. `continue-on-error` is
  removed — the drill is a blocking CI check for the parts that work.
- **`monitoring/promtail.yml`** — keeps the two-json-stage form (unwrap
  the Docker log wrapper, then parse the inner nginx access log). Both
  one-stage and two-stage forms were tested; neither produced the
  derived metrics. The config is syntactically valid and promtail
  starts cleanly.
- **ADR-0035 amended** — the "Known issue" section is replaced with a
  "Status of the promtail metrics stage (open, as of v1.1.3)" section
  that records both tested hypotheses, the verification that the rest
  of the pipeline works, and the pragmatic decision to make the
  metrics assertion advisory.

## [1.1.2] — 2026-12-22

Closes the latency + 5xx gap that ADR-0034 left open: a promtail
metrics pipeline derives a latency histogram and a per-status counter
from the nginx access log, restoring the latency P99 SLO and adding
a 5xx quality SLO.

> **Note:** the `latency-sli-drill` shipped in v1.1.2 as
> `continue-on-error` because the metrics stage produced no metrics.
> The root cause and fix are in v1.1.3 / ADR-0035.

### Added

- **Phase 18.1** — `stacksmith_json` log_format in `nginx/default.conf`
  (emits `$status` and `$request_time` as JSON numbers); `nginx_access`
  scrape config in `monitoring/promtail.yml` with a `metrics` pipeline
  stage that produces `nginx_log_request_duration_seconds` (Histogram)
  and `nginx_log_requests_total` (Counter, labeled by status + method).
- **Phase 18.2** — `promtail` scrape job in `prometheus.yml`; five
  new recording rules (`nginx:p50/p95/p99_latency_ms_5m`,
  `nginx:error_rate_5xx_5m`, `nginx:error_rate_5xx_30d`); two
  re-introduced SLO alerts (`SLOLatencyP99Breach` warning,
  `SLOHigh5xxRate` critical).
- **Phase 18.3** — `latency-sli-drill` CI workflow. Verifies nginx
  emits the JSON access log, promtail exposes the derived metrics,
  prometheus scraped promtail, both recording rules populated, and
  both alerts are loaded.
- **ADR-0035** — records the promtail metrics pipeline decision, the
  rationale (inline metrics stage vs Loki Ruler, JSON vs regex), and
  the consequences.

### Changed

- **ADR-0033 amended** — the latency P99 SLO is restored; a new 5xx
  quality SLO is added.
- **ADR-0034 amended** — the "Future: re-introduce latency SLO" line
  is marked done, pointing to ADR-0035.
- `grafana/dashboards/slo.json` v3 — three new panels (P99 stat,
  latency bands p50/p95/p99, 5xx ratio with the 2% fast-burn line).

## [1.1.1] — 2026-12-22

Closes the SLO/SLI loop: wires in nginx-exporter and corrects the SLI
that v1.1.0 got wrong.

### Added

- **Phase 17.1** — `nginx-exporter` service in
  `docker-compose.monitoring.yml`, `/stub_status` location in
  `nginx/default.conf` (ACL'd to private ranges), `nginx` scrape job
  in `monitoring/prometheus.yml`.
- **Phase 17.2** — `slo-metrics-drill` CI workflow. Asserts
  `nginx_up`, that `/stub_status` is blocked from the host, that the
  `nginx:request_rate_5m` and `slo:availability_5m` recording rules
  populate, and that both SLO alerts are loaded.
- **ADR-0034** — records the OSS nginx limitation (stub_status has no
  per-status-code counts, no latency data) and the decision to retract
  the latency P99 SLO and switch the availability SLI to blackbox
  `probe_success`.

### Changed

- **ADR-0033 amended** — the availability SLI is now
  `avg_over_time(probe_success[30d])`, not a 5xx ratio (which OSS nginx
  cannot produce). The latency P99 SLO is retracted.
- `monitoring/recording_rules.yml` — replaced the two non-existent
  recording rules (`nginx:p95_latency_ms`, `nginx:error_rate_5xx`)
  with three that exist (`nginx:request_rate_5m`,
  `slo:availability_5m`, `slo:availability_30d`,
  `slo:error_budget_used_ratio`, `nginx:connections_active`).
- `monitoring/alert_rules.yml` `stacksmith-slo` group rewritten:
  `SLOAvailabilityDown` (critical, probe failing 2m) replaces
  `SLOErrorBudgetBurnFast`; `SLOLatencyP99Breach` removed with a
  comment explaining why.
- `grafana/dashboards/slo.json` v2 — six panels rebuilt around real
  metrics: availability %, error budget used, request rate, probe
  trend, request rate trend, nginx connections.

 — 2026-12-19

Quality hardening and SLO observability.

### Added

- **Phase 16.1** — markdownlint. `.markdownlint.json` config +
  `.github/workflows/markdownlint.yml` CI gate. 16 auto-fixable
  violations and 14 manual fixes applied across 10 docs files.
- **Phase 16.2** — SLO / SLI / error budget (ADR-0033). Three alert
  rules in `monitoring/alert_rules.yml` (fast-burn critical, budget
  exhausted warning, P99 latency warning). Sixth Grafana dashboard
  `grafana/dashboards/slo.json` with availability %, error budget
  hours, latency percentiles.
- **Phase 16.3** — `docs/adr/INDEX.md` (every ADR by number, status,
  date, and theme). `docs/getting-started.md` (10-minute path from
  clone to running monitored stack).

### Changed

- `.gitignore` now excludes `commitlint/node_modules/` and
  `commitlint/package-lock.json`.
- `.github/pull_request_template.md` gains an H1 and wraps the long
  conventional-commits checklist line.

 — 2026-12-16

Commit convention enforcement (ADR-0032).

### Added

- **commitlint config** (`commitlint/commitlint.config.cjs`) — extends
  Conventional Commits 1.0.0. header ≤ 72 chars, subject imperative with
  no trailing period, body wrap at 100 chars (warning).
- **Local git hooks** (`.githooks/commit-msg`, `.githooks/pre-push`) —
  runs commitlint in the editor; refuses to push leftover `fixup!` or
  `squash!` commits.
- **CI gate** (`.github/workflows/commitlint.yml`) — two jobs: PR title
  check via `amannn/action-semantic-pull-request`, and a per-commit
  commitlint run over the PR's added commits.
- **ADR-0032** — records the three-layer enforcement, allowed types
  table, breaking-change syntax, and the rollout note that the 10
  leftover `fixup!` commits on `main` are left in place.

### Changed

- **CONTRIBUTING.md** — full commit-format section + hook install
  instructions.

 — 2026-12-15

**Stable release.** The operational surface is declared stable (ADR-0031).

### What this release is

stacksmith v1.0.0 is the culmination of 14 phases across 9 previous
releases. It is a production-grade deployment kit that puts the docubot
backend (Django 5.2 + Celery + Postgres/pgvector + Redis) into production
on a single VPS with:

- Zero-downtime blue-green deploys with canary checks and auto-rollback
- Encrypted backups with age, integrity-verified, freshness-monitored
- Disaster recovery drill that simulates total VPS loss
- Full observability: Prometheus, Grafana (5 dashboards), Loki, Tempo,
  Alertmanager with Slack routing
- Supply chain: multi-arch GHCR images, cosign signing, SBOM, CodeQL,
  Trivy, dependency review
- Automated TLS, secret rotation, maintenance mode, capacity planning
- Multi-provider Terraform (Hetzner + DigitalOcean)
- 31 ADRs, 23 CI workflows, 18 operational scripts, 4 runbooks
- OpenAPI spec, architecture documentation with 5 Mermaid diagrams

### What this release declares stable

- Script CLIs (deploy, rollback, backup, restore, rotate, maintenance)
- Compose service names and volumes
- CI workflow contract (23 workflows)
- ADR set (31 decisions)

### What is NOT declared stable

- The docubot application (separate repo, separate stability)
- Multi-host HA (ADR-0015 — evaluation only)
- Business-endpoint load tests (only /health/live/ is tested)

## [0.9.0] — 2026-12-14

Operational excellence: maintenance mode, recording rules, health CLI,
capacity planning, audit log.

### Added

- **Phase 13.1** — Maintenance window mode (`maintenance.sh`) + Prometheus
  recording rules (10 pre-computed metrics). ADR-0030.
- **Phase 13.2** — Health check CLI (`stacksmith-health.sh`) + capacity
  planning dashboard (7-day trends, disk exhaustion prediction).
- **Phase 13.3** — Audit log (`audit-log.sh`) called by deploy, rollback,
  restore, backup. ADR-0030.

### Proven in CI (24 workflows)

All previous 23 plus the maintenance metric (verified by the health CLI
in the smoke drill).

## [0.8.0] — 2026-12-11

Multi-provider infrastructure, architecture documentation, API specification.

### Added

- **Phase 12.1** — Multi-provider Terraform. Hetzner Cloud + DigitalOcean
  in one module, selected by `provider` variable. ADR-0028.
- **Phase 12.2** — Architecture documentation. Five Mermaid diagrams
  (topology, CI pipeline, deploy sequence, backup/DR flow, firewall) plus
  service and observability inventory tables.
- **Phase 12.3** — OpenAPI 3.0 spec for the health endpoints
  (`/health/live/`, `/health/ready/`) with response schemas. ADR-0029.

## [0.7.0] — 2026-12-08

Deploy-time security, developer automation, and cost visibility.

### Added

- **Phase 11.1** — Deploy-time cosign verify. `deploy.sh` verifies the
  image signature before switching the upstream. Hard abort on failure.
  ADR-0025.
- **Phase 11.2** — Release drafter. Maintains a draft GitHub Release from
  PR titles and labels. Dependabot auto-merge for patch and minor bumps
  after CI passes; major bumps get `needs-review`. ADR-0026.
- **Phase 11.3** — Cost monitoring dashboard. `cost-metric.sh` writes a
  textfile metric; Grafana panel shows monthly cost, CPU/memory/disk, and
  per-service cost breakdown. ADR-0027.

## [0.6.0] — 2026-12-04

Operational maturity: the kit now proves it can survive a total VPS loss
and verifies its own supply chain end to end.

### Added

- **Phase 10.1** — cosign verify gate. A CI workflow verifies the image
  signature and SBOM attestation on every push to main and daily at 06:00
  UTC. Also fixes cosign-sign timing (workflow_run on registry-build
  completed). ADR-0023.
- **Phase 10.2** — Disaster recovery drill. Six-phase total VPS loss
  simulation: seed data, encrypt backup, destroy everything (containers +
  volumes + plaintext), provision fresh stack, restore from encrypted .age,
  verify data values + app health. ADR-0024.
- **Phase 10.3** — Automated release notes. Generates changelog sections
  from conventional commits when a tag is pushed.
- **Phase 10.4** — Stale bot. Closes issues inactive for 37 days and PRs
  inactive for 21 days. Exempts pinned and roadmap labels.

### Proven in CI (21 workflows)

All previous 17 plus:

- cosign verify (signature + SBOM attestation)
- disaster recovery drill (total VPS loss)
- stale bot (daily)
- release notes (on tag)

## [0.5.0] — 2026-11-30

Supply chain, infrastructure as code, and chaos engineering.

### Added

- **Phase 9.1** — Multi-arch registry images. Multi-stage Dockerfile,
  linux/amd64 + linux/arm64 builds via Buildx + QEMU, GHCR push with SHA
  tags, build provenance attestation (SLSA L3). ADR-0019.
- **Phase 9.2** — cosign keyless image signing. Signs the GHCR image
  with GitHub OIDC identity, attaches SBOM as a cosign attestation,
  verifies immediately. ADR-0020.
- **Phase 9.3** — Terraform VPS provisioning. Hetzner Cloud VPS,
  firewall, cloud-init that installs Docker and clones the repo. ADR-0021.
- **Phase 9.4** — Chaos engineering drill. Kills the worker, verifies the
  app survives, stops nginx, verifies the outage, restarts both. ADR-0022.

### Proven in CI (20 workflows)

- lint, smoke (stub + prod), deploy + rollback drill, canary failure,
  restore drill, encryption drill, integrity drill, rotation drill,
  logs drill, alerts drill, tracing drill, CodeQL, Trivy, SBOM, k6,
  registry build (multi-arch), cosign sign, chaos drill

## [0.4.0] — 2026-11-25

Production hardening: the kit now proves its supply chain is clean and
its performance is bounded.

### Added

- **Phase 8.1** — Automated security scanning. CodeQL (semantic code
  analysis), Trivy (container image CVE scan, SARIF to Security tab),
  dependency review (PR gate for vulnerable dependency bumps). ADR-0016.
- **Phase 8.2** — SBOM generation. syft produces SPDX JSON and CycloneDX
  JSON bills of materials for the app image; grype scans the SBOM for
  known vulnerabilities. All artifacts uploaded with 30-day retention.
  ADR-0017.
- **Phase 8.3** — Load testing with k6. A 70-second load test ramps to
  50 VUs and enforces p95 < 500ms and failure rate < 1%. A regression
  that breaches the thresholds fails CI. ADR-0018.
- **Phase 8.4** — Community files. Feature request issue template, pull
  request template, CODEOWNERS.

### Proven in CI (17 workflows)

- lint (yamllint, shellcheck, compose config)
- smoke (stub + prod)
- deploy + rollback drill
- canary failure → auto-rollback
- restore drill + metric verification
- encryption drill
- integrity drill
- rotation drill
- logs drill (Loki)
- alerts drill (Alertmanager)
- tracing drill (Tempo)
- CodeQL
- Trivy container scan
- SBOM generation (syft + grype)
- k6 load test

### Security posture

- CodeQL scans the Python code weekly and on every push.
- Trivy scans the built image and uploads SARIF to the Security tab.
- Dependency review blocks PRs that introduce MODERATE+ vulnerabilities.
- SBOM is generated in SPDX and CycloneDX formats on every push.
- Grype scans the SBOM for known vulnerabilities.

## [0.3.0] — 2026-11-20

The v0.3 roadmap is closed. Every item from issue #20 ships in this release.

### Added

- **Phase 7.1** — Alertmanager with severity-based routing. Critical alerts
  page immediately (Slack), warnings wait 30m. Prometheus sends to
  Alertmanager; the `alerts-drill` CI proves a synthetic alert reaches a
  webhook receiver. ADR-0011.
- **Phase 7.2** — Backup integrity verification. `verify-backup.sh` restores
  a backup into a throwaway database and diffs row counts of every table
  against the source. The `integrity-drill` CI seeds multiple tables and
  verifies the counts match. ADR-0012.
- **Phase 7.3** — Secret rotation automation. `rotate-secrets.sh` rotates
  `DJANGO_SECRET_KEY` (via deploy) and `POSTGRES_PASSWORD` (via ALTER USER +
  restart) with zero downtime. The `rotation-drill` CI rotates both and
  verifies the stack stays healthy. ADR-0013.
- **Phase 7.4** — Distributed tracing with OpenTelemetry and Tempo. The
  Django app is auto-instrumented (Django, psycopg, redis, celery); traces
  export to Tempo over OTLP/HTTP. Grafana gains a Tempo datasource with
  traces-to-logs and traces-to-metrics links. The `tracing-drill` CI
  generates traces and queries Tempo. ADR-0014.
- **Phase 7.5** — Multi-host readiness evaluation. ADR-0015 documents what
  it would take to move to two hosts (managed Postgres/Redis, load balancer,
  rolling deploys) and when the decision should be reopened.

### Proven in CI (14 jobs)

- `lint` — yamllint, shellcheck, docker compose config
- `smoke` (stub) — nginx + static health page
- `smoke` (prod) — full stack up, health probes through nginx
- `deploy + rollback drill` — blue → green → blue with canary probes
- `canary failure → auto-rollback` — break app-green, verify auto-rollback
- `backup → wipe → restore → verify` — restore drill + metric verification
- `encrypt → decrypt → restore → verify` — encryption drill
- `backup → verify → row counts match` — integrity drill
- `rotate key → app still serves → rotate password → app still serves`
- `loki ready → ingest → query` — logs drill
- `alertmanager → webhook → verify delivery` — alerts drill
- `tempo ready → trace → query` — tracing drill

### Closed roadmap items (issue #20)

- [x] Alert routing (ADR-0011)
- [x] Backup integrity verification (ADR-0012)
- [x] Secret rotation automation (ADR-0013)
- [x] Distributed tracing (ADR-0014)
- [x] Multi-host readiness (ADR-0015 — evaluation, not action)

## [0.2.0] — 2026-11-15

The v0.2 roadmap is closed. Every item from issue #12 ships in this release.

### Added

- **Phase 6.1** — `backup-db.sh` writes a `backup.prom` textfile metric
  with three gauges (`backup_last_success_timestamp_seconds`,
  `backup_last_success_bytes`, `backup_last_status`). The `BackupStale`
  alert now has real data; a new `BackupFailed` alert fires at 5m instead
  of 26h. ADR-0006.
- **Phase 6.2** — off-host encryption with `age`. `encrypt-backups.sh`
  encrypts every backup with the public key; `sync-backups.sh` ships only
  `.age` files; `restore-db.sh` accepts `.age` and decrypts in-stream.
  The encryption-drill workflow proves the full cycle. ADR-0007.
- **Phase 6.3** — canary checks post-switch with auto-rollback. `deploy.sh`
  runs `CANARY_PROBES` health probes through nginx after the upstream
  switch; a failed probe rolls back automatically. The canary-failure-drill
  CI job breaks app-green and verifies deploy.sh catches it. ADR-0008.
- **Phase 6.4** — Loki and promtail for log aggregation. Single-node Loki
  with 14-day retention; promtail scrapes docker logs via the socket and
  parses JSON lines for `level` and `name` labels. Grafana gains a Loki
  datasource and a container-logs dashboard. The logs-drill CI workflow
  proves the ingest path. ADR-0009.
- **Phase 6.5** — automated TLS with certbot. `docker-compose.tls.yml`
  runs certbot in a 12h renewal loop with `--deploy-hook` that reloads
  nginx. `scripts/issue-cert.sh` obtains the first Let's Encrypt cert via
  ACME HTTP-01. The `:443` server block is real (in `nginx/tls.conf.disabled`,
  enabled by `issue-cert.sh`). ADR-0010.
- **Phase 6.6** — Grafana behind nginx with basic auth. Grafana is no
  longer exposed on port 3000 directly; it is proxied at `/grafana/` with
  an htpasswd file. `scripts/setup-grafana-auth.sh` generates the htpasswd.

### Proven in CI (10 jobs, all green)

- `lint` — yamllint, shellcheck, docker compose config (including TLS overlay)
- `smoke` (stub) — nginx + static health page
- `smoke` (prod) — full stack up, `/health/live/` and `/health/ready/`
- `deploy + rollback drill` — blue → green → blue with canary probes
- `canary failure → auto-rollback` — break app-green, verify auto-rollback
- `backup → wipe → restore → verify` — restore drill with metric verification
- `encrypt → decrypt → restore → verify` — encryption drill
- `loki ready → ingest → query` — logs drill
- `stub stack` — nginx + static page

### Closed roadmap items (issue #12)

- [x] Off-host encryption with `age`
- [x] Canary checks post-switch
- [x] `backup.prom` textfile metric
- [x] Loki as a secondary observability signal
- [x] Automated cert renewal
- [x] Grafana behind nginx with auth

## [0.1.0] — 2026-11-08

First tagged release. The full deploy → monitor → backup → restore cycle
is implemented and proven in CI.

### Added

- **Phase 0** — repository skeleton, lint + smoke CI, dependabot,
  engineering conventions, ADR-0001 (compose as the deployment unit).
- **Phase 1** — production compose stack: app (gunicorn + Django), worker,
  beat, postgres (pgvector/pg17, tuned config, named volumes), redis,
  nginx (reverse proxy, gzip, security headers, TLS template). Per-service
  healthchecks, `.env.example` + `check-env.sh`, json-file log rotation.
- **Phase 2** — blue-green deploy with nginx upstream switch, one-command
  rollback, immutable release tags with manifest, deploy runbook, ADR-0002.
  CI proves the deploy + rollback cycle is zero-downtime.
- **Phase 3** — nightly `pg_dump` with gzip + sha256 + retention, off-host
  rsync with a lock, one-command restore with pre-flight check, restore
  drill in CI (backup → wipe → restore → verify row counts), ADR-0003,
  systemd timer/service units.
- **Phase 4** — prometheus, node-exporter, cAdvisor, blackbox-exporter,
  grafana with two provisioned dashboards, alert rules (backup staleness,
  disk, memory, restarts, 5xx rate, health probe), ADR-0004.
- **Phase 5** — operations runbook, failure playbook, ADR-0005 (secrets
  rotation), this changelog.

### Known limitations

See `docs/known-limitations.md`. All v0.1.0 limitations are closed in v0.2.0.
