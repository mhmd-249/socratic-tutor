"""add_fulltext_search_to_chunks

Revision ID: fc3576e9d2ff
Revises: ec3243cbb0e4
Create Date: 2026-01-06 22:10:30.934025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc3576e9d2ff'
down_revision: Union[str, None] = 'ec3243cbb0e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add tsvector column for full-text search
    op.execute("""
        ALTER TABLE chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
    """)

    # Create GIN index for full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv
        ON chunks
        USING gin(content_tsv);
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop the index and column
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_tsv;")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content_tsv;")
