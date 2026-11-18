# API reference

The stacksmith API surface has two halves, each documented in a
hand-written OpenAPI 3.0.3 spec:

| Spec | Covers | Audience |
| --- | --- | --- |
| [`health-openapi.json`](health-openapi.json) | `GET /health/live/`, `GET /health/ready/`, `GET /` | nginx, blackbox-exporter, the deploy canary, CI drills |
| [`product-openapi.json`](product-openapi.json) | `GET /api/documents/`, `POST /api/documents/`, `POST /api/chat/` | the chat UI, integrators, the rate-limit + upload-validation tests |

## Why hand-written

The specs are hand-written rather than generated from the Django views
because:

- **Stable.** A generated spec drifts with every view refactor; a
  hand-written spec only changes when the contract changes, which is
  what an integrator cares about.
- **Readable.** Each operation carries the why (rate limiting,
  upload validation, dedup) that a code generator cannot infer.
- **No extra dependency.** `drf-spectacular` is the usual generator;
  it pulls a runtime dep and a generation step. The hand-written
  spec is checked in and served as a static file.

The trade-off is that the spec can drift from the code. The unit
suite pins the contracts that matter: the request serializer bounds
(`test_serializers.py`), the upload validation rules
(`test_upload_validation.py`), and the rate-limit policy
(`test_ratelimit.py`). A drift between spec and code surfaces as a
test failure on the code side; the spec is updated in the same PR.

## Validation

The specs are JSON, not YAML, so they parse with any JSON tool. To
validate against the OpenAPI 3.0.3 schema:

```bash
# Using redocly (the canonical OpenAPI linter):
npx --yes @redocly/cli@latest lint docs/api/health-openapi.json docs/api/product-openapi.json
```

A future CI workflow can run that lint on every PR touching
`docs/api/`; until then, run it locally before opening a PR that
changes a spec.

## Browsing

Both specs render in any OpenAPI 3 viewer:

- [Swagger UI online](https://editor.swagger.io/) — paste the JSON.
- [Redoc](https://redocly.github.io/redoc/) — same.
- Local: `npx --yes @redocly/cli@latest preview-docs docs/api/product-openapi.json`
