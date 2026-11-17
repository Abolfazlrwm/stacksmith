# ADR-0037: app hardening — fail-closed defaults, upload validation, unit tests

- **Status:** accepted
- **Date:** 2026-11-17
- **Supersedes:** none (complements ADR-0016 security scanning and ADR-0036 the docubot product surface)

## Context

v1.2.0 shipped the docubot product surface (ADR-0036): a documents
upload API, RAG retrieval, and a chat endpoint with citations. The
product works end-to-end and the container drills prove it, but three
gaps were visible on a close read of `app/config/settings.py` and
`app/documents/views.py`:

1. **`ALLOWED_HOSTS` defaulted to `*`.** A misconfigured prod deploy
   would answer any Host header. nginx's `server_name _;` catches the
   obvious case, but the app should fail closed on its own — defense
   in depth, and the readiness probe hits Django directly, not nginx.

2. **The upload path trusted the client's filename and content-type
   header.** `detect_kind` mapped any `.pdf` extension to the PDF
   extractor without checking that the bytes actually start with
   `%PDF-`. A multipart payload named `evil.pdf` but containing an EXE
   would land on the upload volume as a `.pdf` and be queued for
   ingestion. (Ingestion would then fail on the EXE bytes, but the
   bytes would already be on disk.) A second issue: `detect_kind`'s
   `endswith` tuple included `""`, and `str.endswith("")` always
   returns True — so `evil.exe` was silently classified as `text`.

3. **No Python unit tests existed.** The repo had container drills
   (restore, DR, chaos, encryption) and a k6 load test, but nothing
   exercised the pure functions in `documents/ingestion.py` or the
   citation resolver in `chat/views.py`. A regression in
   `_resolve_citations` would only surface in a 4-minute container
   drill, if it surfaced at all.

## Decision

### 1. Fail-closed defaults for the app's security settings

`ALLOWED_HOSTS` defaults to `docubot.example.com,localhost,127.0.0.1`.
Operators override via `DJANGO_ALLOWED_HOSTS`; the local-dev value
already exists in `.env.example`. The wildcard is gone.

`SecurityMiddleware` is the first middleware. `SECURE_PROXY_SSL_HEADER`
reads `X-Forwarded-Proto` (set by nginx). `SECURE_SSL_REDIRECT` and
HSTS (1 year, preload, include-subdomains) are enabled when
`DEBUG=false`. `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`,
and `X_FRAME_OPTIONS=DENY` are set on every response. HSTS is
disabled in local dev so a `curl http://localhost` does not
infinite-redirect. `/health/*` is exempt from the SSL redirect so the
in-container readiness probe can reach the app over plain HTTP.

`CsrfViewMiddleware` and `XFrameOptionsMiddleware` are added as
defense-in-depth. The chat and documents APIs are not CSRF-protected
today (the reverse proxy authenticates and sets `X-Docubot-Owner`),
but the admin and any future session-backed view will be.

### 2. Upload validation at the app boundary

`documents.ingestion.validate_upload(filename, data)` is the single
security gate on the upload path. It runs BEFORE any bytes are written
to disk and enforces three layers:

- **Extension allow-list**: `{.pdf, .md, .markdown, .txt, .text}`.
  Anything else is refused with a 400. This is the cheap first filter.
- **Magic-byte sniff**: for kinds with a known signature (PDF today:
  `%PDF-`), the first bytes of the content must match. Defeats
  name-spoofing where an attacker renames a binary to `.pdf`.
- **UTF-8 decode check**: for text and markdown (no portable magic
  bytes), the bytes must decode as UTF-8. A renamed binary fails here.

The view also rejects filenames containing `/` or `\` or any path
component (storage is keyed by checksum, but the name is echoed in
the response), and caps filename length at 255 chars before any disk
I/O.

The `endswith("")` bug in `detect_kind` is fixed: the empty-string
fallback is gone; the `text/plain` MIME fallback still handles
extension-less files like `Makefile`.

### 3. Pure-function unit tests, run in CI

`tests/app/` is a pytest suite of 45 tests targeting the pure
functions in `documents/ingestion.py` and the citation resolver in
`chat/views.py`. `conftest.py` builds a minimal Django settings
module in-memory with only the four docubot apps loaded, so
app-loading never opens a DB connection. The suite runs in <1s with
no pgvector, no Redis, no LLM.

`.github/workflows/app-tests.yml` runs the suite on every push that
touches app code or tests, and on every PR to `main`. The job
installs only the deps the suite imports (Django, DRF, pgvector,
cors-headers, celery, redis, psycopg, markdown, pytest) and skips
torch + sentence-transformers (~2 GB) because the tests stub out the
embedding and LLM calls. That keeps the job under a minute.

## Alternatives considered

- **Rely on nginx alone for security headers.** Rejected: the canary
  probe and the in-container readiness check hit Django directly,
  and the proxy is a single point of failure for the security
  posture. The app must fail closed on its own.

- **Use a real PDF parser to validate uploads.** Rejected: PyMuPDF
  already validates during ingestion; a second parse on the request
  path doubles the CPU cost of every upload for marginal benefit.
  The magic-byte check is enough to defeat name-spoofing; the real
  parse happens in the ingest task.

- **Run the existing container drills instead of adding unit tests.**
  Rejected: the drills prove the whole stack works end-to-end, but
  they take minutes per run and do not exercise edge cases like
  `evil.exe` or `[0]` citation markers. Unit tests are the fast
  feedback loop; drills are the slow proof. Both are needed.

- **Use Django's test runner instead of pytest.** Rejected: the
  Django test runner requires a database for the ORM-backed tests we
  do not yet have. pytest runs the pure-function tests today and
  will scale to ORM tests when we add them (via `pytest-django`).

## Consequences

- A misconfigured prod deploy (`DJANGO_ALLOWED_HOSTS` unset) now
  answers 400 Bad Request instead of the requested host. This is
  the intended fail-closed behavior; operators must set the env var.
- The upload path is stricter: a previously-accepted `.docx` upload
  now returns 400. The README and the API docs already list the
  accepted kinds; this is a tightening, not a regression.
- The test suite is a new CI gate. A push that breaks a unit test
  cannot merge. The suite is fast (<1s locally, <1min in CI) so the
  cost is low.
- `detect_kind` no longer accepts bare-stem filenames by extension
  alone — it requires a `text/plain` MIME. The `Makefile` case still
  works because the upload view passes the content-type header.
