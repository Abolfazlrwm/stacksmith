"""Add an HNSW index on the Chunk embedding column for fast ANN search.

pgvector supports ivfflat and hnsw; we choose hnsw because it has better
recall at low volume and does not require a separate training step. The
index is built with cosine distance to match the retrieval query operator.

`atomic = False` is required because `CREATE INDEX CONCURRENTLY` cannot
run inside a transaction block — Postgres needs to see intermediate
commits to allow concurrent writes while the index builds. This matches
the pattern used by `health/0001_enable_pgvector.py`.
"""
from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS chunk_embedding_hnsw "
                "ON documents_chunk USING hnsw (embedding vector_cosine_ops);"
            ),
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS chunk_embedding_hnsw;",
        ),
    ]
