"""Chapter repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.repositories.base import BaseRepository


class ChapterRepository(BaseRepository[Chapter]):
    """Repository for Chapter model."""

    def __init__(self, session: AsyncSession):
        """Initialize chapter repository."""
        super().__init__(Chapter, session)

    async def get_by_book(self, book_id: UUID) -> list[Chapter]:
        """
        Get all chapters for a book.

        Args:
            book_id: Book UUID

        Returns:
            List of chapters ordered by chapter_number
        """
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.book_id == book_id)
            .order_by(Chapter.chapter_number)
        )
        return list(result.scalars().all())

    async def get_by_chapter_number(
        self, book_id: UUID, chapter_number: int
    ) -> Chapter | None:
        """
        Get a chapter by its number within a book.

        Args:
            book_id: Book UUID
            chapter_number: Chapter number

        Returns:
            Chapter instance or None if not found
        """
        result = await self.session.execute(
            select(Chapter).where(
                Chapter.book_id == book_id,
                Chapter.chapter_number == chapter_number,
            )
        )
        return result.scalar_one_or_none()
