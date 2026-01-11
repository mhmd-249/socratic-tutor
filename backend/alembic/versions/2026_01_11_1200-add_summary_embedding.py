"""Add embedding column to conversation_summaries table.

Revision ID: add_summary_embedding
Revises: fc3576e9d2ff
Create Date: 2026-01-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'add_summary_embedding'
down_revision: Union[str, None] = 'fc3576e9d2ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add embedding column (nullable to support existing records)
    op.add_column(
        'conversation_summaries',
        sa.Column('embedding', Vector(1536), nullable=True)
    )

    # Create index for vector similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_conversation_summaries_embedding
        ON conversation_summaries
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.drop_index('ix_conversation_summaries_embedding', table_name='conversation_summaries')
    op.drop_column('conversation_summaries', 'embedding')
