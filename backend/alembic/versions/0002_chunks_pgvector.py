"""chunks with pgvector embeddings and full-text search

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match EMBEDDING_DIM (bge-small-en-v1.5 = 384). Changing models = new migration + re-ingest.
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            section VARCHAR(1000),
            page INTEGER,
            content_hash VARCHAR(64) NOT NULL,
            embedding vector({EMBEDDING_DIM}) NOT NULL,
            embedding_model VARCHAR(200) NOT NULL,
            tsv TSVECTOR GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(section, '')), 'A') ||
                setweight(to_tsvector('english', content), 'B')
            ) STORED,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_owner_id ON chunks (owner_id)")
    op.execute(
        "CREATE UNIQUE INDEX ix_chunks_document_id_chunk_index ON chunks (document_id, chunk_index)"
    )
    # HNSW: approximate nearest-neighbour index; cosine distance to match normalized embeddings.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunks")
