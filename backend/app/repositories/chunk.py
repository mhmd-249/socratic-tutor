"""Chunk repository."""

from uuid import UUID

from sqlalchemy import select, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository for Chunk model."""

    def __init__(self, session: AsyncSession):
        """Initialize chunk repository."""
        super().__init__(Chunk, session)

    async def get_by_chapter(
        self, chapter_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Chunk]:
        """
        Get all chunks for a chapter.

        Args:
            chapter_id: Chapter UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chunks ordered by chunk_index
        """
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.chapter_id == chapter_id)
            .order_by(Chunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_embedding(
        self, embedding: list[float], chapter_id: UUID | None = None, limit: int = 5
    ) -> list[Chunk]:
        """
        Search for similar chunks using vector similarity.

        Args:
            embedding: Query embedding vector
            chapter_id: Optional chapter ID to filter results
            limit: Maximum number of results to return

        Returns:
            List of most similar chunks
        """
        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        # Build query with optional chapter filter
        if chapter_id:
            query = text(
                """
                SELECT * FROM chunks
                WHERE chapter_id = :chapter_id
                ORDER BY embedding <-> (:embedding)::vector
                LIMIT :limit
                """
            ).bindparams(
                bindparam("chapter_id", value=chapter_id),
                bindparam("embedding", value=embedding_str),
                bindparam("limit", value=limit),
            )
            result = await self.session.execute(query)
        else:
            query = text(
                """
                SELECT * FROM chunks
                ORDER BY embedding <-> (:embedding)::vector
                LIMIT :limit
                """
            ).bindparams(
                bindparam("embedding", value=embedding_str),
                bindparam("limit", value=limit),
            )
            result = await self.session.execute(query)

        # Convert rows to Chunk instances
        chunks = []
        for row in result:
            chunk = Chunk(
                id=row.id,
                chapter_id=row.chapter_id,
                content=row.content,
                embedding=row.embedding,
                chunk_index=row.chunk_index,
                section_title=row.section_title,
                chunk_metadata=row.chunk_metadata,
                created_at=row.created_at,
            )
            chunks.append(chunk)

        return chunks
