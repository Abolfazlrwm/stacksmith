# ADR-0037: app hardening — fail-closed defaults, upload validation

- **Status:** accepted
- **Date:** 2026-11-17
- **Supersedes:** none (complements ADR-0016 security scanning and ADR-0036 the docubot product surface)

## Context

v1.2.0 shipped the docubot product surface (ADR-0036): a documents
upload API, RAG retrieval, and a chat endpoint with citations. The
v1.2.1 test suite (commit `07bc21e`) added 70 unit tests and surfaced
one real bug — `detect_kind`'s `endswith` tuple contained an empty
string, so `evil.exe` was silently classified as `text`. That bug is
fixed on main.

But three gaps remained on a close read of `app/config/settings.py`
and `app/documents/views.py`:

1. **`ALLOWED_HOSTS` defaulted to `*`.** A misconfigured prod deploy
   would answer any Host header. nginx's `server_name _;` catches the
   obvious case, but the app should fail closed on its own — defense
   in depth, and the readiness probe hits Django directly, not nginx.

2. **The upload path trusted the client's filename.** `detect_kind`
   mapped any `.pdf` extension to the PDF extractor without checking
   that the bytes actually start with `%PDF-`. A multipart payload
   named `evil.pdf` but containing an EXE would land on the upload
   volume as a `.pdf` and be queued for ingestion. (Ingestion would
   then fail on the EXE bytes, but the bytes would already be on disk,
   and the dedup-by-checksum path would have already created a row.)

3. **No `SECURE_*` headers set by the app.** nginx set them, but the
   canary probe and any direct port-8000 access (local dev, the
   in-container readiness probe) saw unhardened responses.

## Decision

### 1. Fail-closed defaults for the app's security settings

`ALLOWED_HOSTS` defaults to `docubot.example.com,localhost,127.0.0.1`.
Operators override via `DJANGO_ALLOWED_HOSTS`; the local-dev value
already exists in `.env.example` (set to `*` for convenience). The
wildcard is gone from the default.

`SecurityMiddleware` is the first middleware. `CsrfViewMiddleware` and
`XFrameOptionsMiddleware` are added as defense-in-depth. The chat and
documents APIs are not CSRF-protected today (the reverse proxy
authenticates and sets `X-Docubot-Owner`), but the admin and any
future session-backed view will be — adding the middleware now is
purely additive and costs nothing.

### 2. `SECURE_*` headers — response-only, safe to set unconditionally

`SECURE_PROXY_SSL_HEADER` reads `X-Forwarded-Proto` (set by nginx).
`SECURE_HSTS_SECONDS` is 1 year when `DEBUG=false`, 0 in local dev (HSTS
has no effect over plain HTTP anyway, but a clean dev curl is nicer
than one that gets a `Strict-Transport-Security` header it will never
use). `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, and
`X_FRAME_OPTIONS=DENY` are set on every response.

These are all response-header-only — they never affect request routing,
so they cannot break a health probe. This is the key property: any
setting that changes request routing must be opt-in (see §3).

### 3. `SECURE_SSL_REDIRECT` is opt-in, default off

An earlier draft of this release turned `SECURE_SSL_REDIRECT` on when
`DEBUG=false`. That broke every container drill in CI: the in-container
readiness probe and the blue/green canary probe hit the app over plain
HTTP (nginx has not terminated TLS at that point in the deploy
sequence), so the redirect made every probe see `301` forever and the
stack never reported healthy. Nine drills failed simultaneously.

The redirect is now controlled by `DJANGO_SSL_REDIRECT=true` and is
intended for the rare case where the app is directly internet-facing.
In the normal deploy (nginx terminates TLS), nginx handles the
http→https redirect; the app never sees a plain-HTTP request from a
real client. `/health/*` is exempt from the redirect as
belt-and-suspenders, so even with the redirect on, the probe still
sees a `200`.

### 4. Upload validation at the app boundary

`documents.ingestion.validate_upload(filename, data)` is the single
security gate on the upload path. It runs BEFORE any bytes are written
to disk and enforces three layers:

- **Extension allow-list**: `{.pdf, .md, .markdown, .txt, .text}`.
  Anything else is refused with a 400. This is the cheap first filter.
- **Magic-byte sniff**: for kinds with a known signature (PDF today:
  `%PDF-`), the first bytes of the content must match. Defeats
  name-spoofing where an attacker renames a binary to `.pdf`.
- **UTF-8 decode check**: for text and markdown (no portable magic
  bytes), the bytes must decode as UTF-8. A renamed binary fails here
  instead of producing garbage chunks with U+FFFD replacements.

The view also rejects filenames containing `/` or `\` or any path
component (storage is keyed by checksum, but the name is echoed in
the response), and caps filename length at 255 chars before any disk
I/O.

## Alternatives considered

- **Rely on nginx alone for security headers.** Rejected: the canary
  probe and the in-container readiness check hit Django directly, and
  the proxy is a single point of failure for the security posture.
  The app must fail closed on its own.

- **Use a real PDF parser to validate uploads.** Rejected: PyMuPDF
  already validates during ingestion; a second parse on the request
  path doubles the CPU cost of every upload for marginal benefit. The
  magic-byte check is enough to defeat name-spoofing; the real parse
  happens in the ingest task.

- **Turn on `SECURE_SSL_REDIRECT` when `DEBUG=false`.** Tried, broke
  CI, reverted to opt-in. Documented above.

- **Add a separate `app-tests.yml` CI workflow.** Rejected: main's
  `unit.yml` workflow already installs the dependency subset (filters
  `torch`/`sentence-transformers` out of `app/requirements.txt`) and
  runs `pytest app/tests`. Reusing it keeps one canonical gate for
  unit tests and avoids two workflows running the same suite.

## Consequences

- A misconfigured prod deploy (`DJANGO_ALLOWED_HOSTS` unset) now
  answers 400 Bad Request instead of the requested host. This is the
  intended fail-closed behavior; operators must set the env var.
- The upload path is stricter: a previously-accepted `.docx` upload
  now returns 400. The README and the API docs already list the
  accepted kinds; this is a tightening, not a regression.
- The test suite grows by 19 tests (70 → 89). The new tests pin the
  exact `ALLOWED_EXTENSIONS` set so a future change to it fails the
  test and forces a docs update.
- `conftest.py` prepends `testserver` to `DJANGO_ALLOWED_HOSTS` before
  `django.setup()` so the closed default does not break Django's test
  client. Production behavior is unchanged.
