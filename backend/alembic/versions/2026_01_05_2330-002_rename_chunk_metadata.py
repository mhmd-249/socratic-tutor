"""Rename chunk metadata column

Revision ID: 002
Revises: 001
Create Date: 2026-01-05 23:30:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Rename metadata column to chunk_metadata in chunks table
    op.execute('ALTER TABLE chunks RENAME COLUMN metadata TO chunk_metadata')


def downgrade() -> None:
    """Downgrade database schema."""
    # Rename back to metadata
    op.execute('ALTER TABLE chunks RENAME COLUMN chunk_metadata TO metadata')
