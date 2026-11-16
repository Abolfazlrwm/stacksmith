# Security model

docubot never sends document text to a third party. The only outbound call
is the LLM completion, and the operator chooses the provider. When the
provider is OpenAI or Anthropic, the retrieved passages (not the whole
corpus) are sent as context for that single completion. When the provider
is a local Ollama instance, nothing leaves the host at all.

Uploaded files are stored on a Docker volume mounted into the API and
worker containers only. They are SHA-256 deduplicated; the same file
uploaded twice returns the existing document row without re-ingestion.
Each chunk's embedding is stored in pgvector; the column is indexed with
HNSW for fast approximate nearest-neighbor search.

Multi-user isolation is enforced at the database query level: every
retrieval query is scoped by the `owner` column, which is set from the
`X-Docubot-Owner` header that the reverse proxy injects after performing
its own authentication. A user can never retrieve chunks belonging to
another owner.

Image signatures are verified with cosign both in CI (on every push) and at
deploy time (before the nginx upstream is switched). A tampered image
refuses to deploy.
