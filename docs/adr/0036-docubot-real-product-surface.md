# ADR-0036: docubot — real product surface, not a health-check stub

- **Status:** accepted
- **Date:** 2026-11-16
- **Supersedes:** none (complements ADR-0028 multi-provider and ADR-0033 SLOs)

## Context

Through v1.1.x, the `app/` directory was a Django stub: a health-check
endpoint, pgvector extension enabled, Celery + OTel wired up, but no
actual product. The README and the product deck described docubot as a
document-chat assistant with RAG over pgvector, multi-user collections,
and citations — none of which existed in code. A visitor who read the
deck and then opened the repo would find a polished operations surface
around an empty room.

This was a deliberate choice up to v1.0: the kit's job was to be the
operability layer, and the product was a separate concern. v1.2 is the
point where the product catches up, because:

- The deck, the README, and the ADRs now make claims the code does not
  back. Closing that gap is cheaper than re-issuing the deck.
- The k6 load test could only hit `/health/live/` — there was no other
  endpoint to load-test. known-limitations.md called this out explicitly.
- The deploy drill, the cosign-at-deploy gate, and the SLO dashboard
  all describe a product that takes traffic. Without one, the drills
  are exercises, not proofs.

## Decision

Ship three Django apps that together implement the product described in
the README:

### `documents` — ingestion

- `Document` model: owner-scoped, SHA-256 deduplicated, lifecycle of
  pending → ingesting → ready → failed. PDF, Markdown, and plain-text
  kinds; raw bytes persisted to a volume, not the database.
- `Chunk` model: a `text` column plus a 384-dim pgvector `embedding`.
  Chunks are ~2,000 characters with ~10% overlap, so a passage that
  straddles a boundary is still retrievable.
- Celery task `ingest_document`: extract text (PyMuPDF for PDF, a
  markdown-stripping pass for MD, UTF-8 decode for TXT), split into
  chunks, embed in one batch, `bulk_create` the rows. Idempotent:
  re-running on an already-ready document is a no-op; re-running on a
  failed document clears the partial chunks and starts over.

### `rag` — embeddings and retrieval

- `embed_texts`: dispatches on `DOCUBOT_EMBED_PROVIDER`. Default is
  `local` — sentence-transformers `all-MiniLM-L6-v2` (384-dim, ~90 MB),
  running on the same VPS as the app so document text never leaves the
  host. OpenAI is supported for operators who already pay for the API
  and want 1536-dim vectors. A `stub` provider (deterministic
  hash-based vectors) exists for CI and `make demo`.
- `retrieve`: cosine-distance ANN search over the HNSW index on
  `documents_chunk.embedding`, scoped by `owner` so user A never
  retrieves user B's chunks. Returns `RetrievalHit` dataclasses with
  the chunk text, document title, and similarity score.

### `chat` — the API and the conversation

- `POST /api/chat/` with `{question, conversation_id?, top_k?}`.
  Retrieves the top-k chunks, passes them as context to the LLM
  adapter, persists the user message and the assistant answer (with
  structured citations), and returns the answer plus the citations.
- LLM adapter dispatches on `DOCUBOT_LLM_PROVIDER`: `openai`,
  `anthropic`, `ollama` (local, no outbound traffic), or `stub`. The
  system prompt instructs the model to answer only from context and
  cite by `[1]`, `[2]`, … — the view resolves those markers back to
  the actual chunks.
- `GET /api/documents/` lists the owner's documents with status, so
  the UI can show an ingestion progress indicator. `POST /api/documents/`
  accepts a multipart upload and enqueues ingestion via a `post_save`
  signal.
- A single-page HTML chat UI at `/app/` — self-contained, no build
  step, served by Django's template engine. Sidebar for upload +
  document list, main pane for the chat thread with rendered
  citations.

### Multi-user isolation

Every retrieval and every document-list query is scoped by `owner`,
set from the `X-Docubot-Owner` header. The README documents that the
operator must set this header in nginx after performing their own
authentication; a future phase can swap it for a real session/JWT
without changing the views.

### Demo and load test

- `make demo` runs `scripts/demo.py`, which ingests the sample corpus
  under `tests/demo-corpus/`, waits for ready, and asks a question
  through the chat API — printing the answer and its citations. With
  `DOCUBOT_LLM_PROVIDER=stub` and `DOCUBOT_EMBED_PROVIDER=stub` it
  runs without any model download or LLM credentials.
- `tests/load/chat-k6.js` is a k6 script that POSTs to `/api/chat/`
  with a small pool of questions cycled across iterations. The
  `load-test` workflow's new `k6-chat` job seeds the corpus, then
  runs k6 with stub providers, asserting P95 < 2.5s and < 5% business
  failures.

## Rationale

- **Local embeddings by default.** The whole point of self-hosting
  docubot is that documents do not leave the host. A local model
  makes that true for ingestion too, not just chat. OpenAI is opt-in
  for operators who have already accepted the trade-off.
- **`all-MiniLM-L6-v2`, not a larger model.** It is 90 MB, runs on
  CPU in well under a second per batch, and is good enough for the
  short-form documents this kit targets (runbooks, FAQs, ADRs). A
  larger model is a one-line change in `embeddings.py` plus a
  dimension migration.
- **HNSW over ivfflat.** HNSW does not need a training step, has
  better recall at low volume, and is the default recommendation in
  the pgvector docs.
- **Stub providers.** CI and `make demo` need to exercise the full
  pipeline without a model download (slow, flaky) or LLM credentials
  (a secret to manage). The stub LLM returns a deterministic answer
  that cites `[1]`; the stub embeddings are hash-based so retrieval
  still returns real chunks. They are documented as not for
  production.
- **Single-page HTML, no React, no build.** The UI is a tool, not a
  product. A 600-line HTML file is easier to maintain than a Node
  toolchain, and it ships inside the same image.
- **Citations are resolved by the view, not the model.** The model
  emits `[1]`/`[2]` markers; the view parses them and maps to actual
  chunks. This means the structured citation is always truthful — it
  can never point at a chunk that was not in the context — and a model
  that does not cite at all still gets the retrieved hits back, ranked
  by score.

## Consequences

- **Positive:** the README, the deck, and the ADRs now describe code
  that exists. `make demo` proves the product end-to-end. The k6 load
  test finally exercises a business endpoint.
- **Positive:** the deploy drill and the SLO dashboard now describe a
  system that takes real traffic.
- **Negative:** the image is larger. sentence-transformers + torch
  (CPU) + PyMuPDF add roughly 800 MB to the runtime image. This is
  acceptable on a single VPS; if it becomes a problem, the local
  provider can be moved to a sidecar.
- **Negative:** the first ingestion after a fresh deploy is slow —
  the model is downloaded on first use (~90 MB). Operators who want a
  cold-start-free deploy can pre-populate the HF cache in the image.
- **Negative:** multi-user isolation is enforced at the query layer,
  not the database layer. A bug in a `filter(owner=...)` is a
  cross-user data leak. A future phase should add row-level security
  in Postgres as defense-in-depth.

## Rollout

1. `documents/`, `rag/`, `chat/` apps added under `app/`.
2. `requirements.txt` extended with DRF, pgvector, sentence-transformers,
  torch (CPU), PyMuPDF, markdown, openai, anthropic, httpx,
  django-cors-headers, python-magic.
3. Migrations: `documents/0001_initial`, `documents/0002_chunk_embedding_hnsw`
  (creates the HNSW index concurrently), `chat/0001_initial`.
4. `config/settings.py` extended: the three apps, DRF + CORS config,
  the `DOCUBOT_UPLOAD_ROOT` volume, templates dir, admin plumbing.
5. `config/urls.py` extended: `/api/documents/`, `/api/chat/`, `/admin/`,
  `/app/` (chat UI).
6. `app/templates/chat.html` — the single-page chat UI.
7. `scripts/demo.py` + `tests/demo-corpus/` + `make demo` target.
8. `tests/load/chat-k6.js` + the `k6-chat` job in `load-test.yml`.
9. This ADR and the v1.2.0 changelog entry.
