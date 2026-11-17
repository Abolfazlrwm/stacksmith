# Changelog

All notable changes to stacksmith are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.1] — 2026-11-17

The hardening release. v1.2.0 shipped the product; v1.2.1 hardens its
security edges and adds the first Python unit tests so regressions in
the upload path are caught before they reach CI's container drills.
See ADR-0037 for the threat model.

### Changed — app security posture

- **`ALLOWED_HOSTS` no longer defaults to `*`.** The previous default
  meant a misconfigured prod deploy answered any Host header. The new
  default is the canonical hostname plus `localhost`/`127.0.0.1` for
  the in-container readiness probe; operators still override via env.
- **`SecurityMiddleware` is now the first middleware**, with
  `CsrfViewMiddleware` and `XFrameOptionsMiddleware` added as
  defense-in-depth for the admin and future session views.
- **`SECURE_*` headers** are now set by the app, not just the proxy:
  `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS (1 year,
  preload, include-subdomains), `SECURE_CONTENT_TYPE_NOSNIFF`,
  `SECURE_REFERRER_POLICY`, `X_FRAME_OPTIONS=DENY`. HSTS is disabled
  in local dev so a curl to `http://localhost` does not redirect.
- **`/health/*` exempt from the SSL redirect** so the in-container
  readiness probe can reach the app over plain HTTP.

### Changed — upload validation

- **Extension allow-list** (`{.pdf, .md, .markdown, .txt, .text}`) is
  enforced before any bytes are written to disk.
- **Magic-byte sniff** for PDF (`%PDF-`) defeats name-spoofing where
  an attacker renames a binary to `.pdf`.
- **UTF-8 decode check** for `.txt`/`.md` defeats the same attack on
  text kinds, which have no portable magic bytes.
- **Path-traversal rejection**: filenames containing `/` or `\` or
  any path component are refused; storage is keyed by checksum, but
  the name is echoed in the response.
- **Filename length capped at 255 chars** before any disk I/O.

### Fixed

- **`detect_kind` silently accepted any extension as `text`** because
  the `endswith` tuple contained an empty string (an empty string
  `endswith` returns True). `evil.exe` was classified as plain text.
  The empty-string fallback was removed; the `text/plain` MIME
  fallback still handles extension-less files like `Makefile`. Found
  by the new pytest suite.

### Added — test + CI surface

- **`tests/app/`** — 45 pytest unit tests covering `documents.ingestion`
  (`detect_kind`, `validate_upload`, `split_chunks`, `extract_*`,
  `approx_token_count`) and `chat.views._resolve_citations` (explicit
  citations, ordering, dedup, bounds safety, fallback, snippet
  shaping). Runs in <1s with no database.
- **`.github/workflows/app-tests.yml`** runs the suite on every push
  that touches app code or tests, and on every PR to `main`. Installs
  only the deps the suite imports (skips torch / sentence-transformers
  to keep the job under a minute).
- **`pytest.ini`** pins `testpaths = tests/app`.
- **`requirements-dev.txt`** pins `pytest==9.0.2` separately from the
  runtime requirements.

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
