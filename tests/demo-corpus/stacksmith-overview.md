# docubot demo corpus — three short documents a new operator can use to
# see the product answer questions end-to-end. These are committed so
# `make demo` is self-contained.

# doc 1 — a one-pager about the product itself
**StackSmith overview.** StackSmith is the production deployment kit for
docubot. It runs on a single VPS with no Kubernetes and no cloud lock-in.
The stack includes nginx, Postgres with pgvector, Redis, Celery, Prometheus,
Loki, Tempo, Alertmanager, and Grafana. Backups are encrypted with age and
copied off-host. Deploys are blue-green with canary probes and auto-rollback.

The product, docubot, is a self-hosted document-chat assistant. Users upload
PDFs, Markdown, and plain-text documents, then ask questions of them in a
chat interface. Answers are grounded in the user's own documents via
retrieval-augmented generation (RAG) over a pgvector index. No document data
leaves the host; the only outbound call is the LLM completion, and the
operator chooses the provider (OpenAI, Anthropic, or a local Ollama model).

# doc 2 — runbook-style facts
**Operational facts.** The default embedding model is all-MiniLM-L6-v2,
which produces 384-dimensional vectors and runs on the same VPS as the app.
SLOs are: 99.5% availability over 30 days, P99 latency under 500ms, and a
5xx ratio below 2%. Backup freshness is exposed as a Prometheus textfile
metric, and alerts fire if a backup is older than 24 hours or fails outright.
The disaster recovery drill destroys and rebuilds the stack from an encrypted
backup; it is run in CI on every push.

# doc 3 — a short story with specific numbers
**Capacity and cost.** A single 4-vCPU / 8 GB VPS comfortably serves a
small team of up to 50 concurrent users with a corpus of roughly 10,000
documents. Monthly cost is dominated by the VPS itself (about $12 on
Hetzner CX32) plus the chosen LLM provider; with OpenAI gpt-4o-mini at
default settings, expect around $0.40 per 1,000 chat turns. Storage grows
by approximately 2 KB per chunk plus the 384-dim vector (1.5 KB), so a
10,000-document corpus with an average of 20 chunks each is about 700 MB
in Postgres.
