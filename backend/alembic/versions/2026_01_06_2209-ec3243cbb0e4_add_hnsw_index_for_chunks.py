"""add_hnsw_index_for_chunks

Revision ID: ec3243cbb0e4
Revises: 002
Create Date: 2026-01-06 22:09:09.989157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec3243cbb0e4'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create HNSW index on chunks.embedding for fast cosine similarity search
    # m=16: number of connections per layer (default, good balance)
    # ef_construction=64: size of dynamic candidate list (higher = better quality, slower build)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop HNSW index
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw;")
