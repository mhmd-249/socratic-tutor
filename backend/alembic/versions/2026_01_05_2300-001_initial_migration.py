"""Initial migration with all models

Revision ID: 001
Revises:
Create Date: 2026-01-05 23:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create enum types
    op.execute("CREATE TYPE conversation_status AS ENUM ('active', 'completed', 'abandoned')")
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system')")

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supabase_id', sa.String(), nullable=False, unique=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_supabase_id', 'users', ['supabase_id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Create books table
    op.create_table(
        'books',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_books_title', 'books', ['title'])

    # Create chapters table
    op.create_table(
        'chapters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('prerequisites', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('key_concepts', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_chapters_book_id', 'chapters', ['book_id'])
    op.create_index('ix_chapters_title', 'chapters', ['title'])

    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('chapter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('section_title', sa.String(), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_chunks_chapter_id', 'chunks', ['chapter_id'])

    # Create vector index for similarity search
    op.execute('CREATE INDEX ix_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)')

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chapter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'completed', 'abandoned', name='conversation_status'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_chapter_id', 'conversations', ['chapter_id'])
    op.create_index('ix_conversations_started_at', 'conversations', ['started_at'])
    op.create_index('ix_conversations_status', 'conversations', ['status'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'assistant', 'system', name='message_role'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # Create conversation_summaries table
    op.create_table(
        'conversation_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('topics_covered', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('concepts_understood', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('concepts_struggled', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('questions_asked', sa.Integer(), nullable=False),
        sa.Column('engagement_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_conversation_summaries_conversation_id', 'conversation_summaries', ['conversation_id'])

    # Create learning_profiles table
    op.create_table(
        'learning_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('mastery_map', postgresql.JSONB(), nullable=False),
        sa.Column('identified_gaps', postgresql.JSONB(), nullable=False),
        sa.Column('strengths', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('recommended_chapters', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('total_study_time_minutes', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_learning_profiles_user_id', 'learning_profiles', ['user_id'])


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table('learning_profiles')
    op.drop_table('conversation_summaries')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('chunks')
    op.drop_table('chapters')
    op.drop_table('books')
    op.drop_table('users')

    op.execute('DROP TYPE message_role')
    op.execute('DROP TYPE conversation_status')
    op.execute('DROP EXTENSION vector')
