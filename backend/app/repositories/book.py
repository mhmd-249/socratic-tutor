"""Book repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.repositories.base import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Repository for Book model."""

    def __init__(self, session: AsyncSession):
        """Initialize book repository."""
        super().__init__(Book, session)

    async def get_by_title(self, title: str) -> list[Book]:
        """
        Get books by title (partial match).

        Args:
            title: Book title to search for

        Returns:
            List of matching books
        """
        result = await self.session.execute(
            select(Book).where(Book.title.ilike(f"%{title}%"))
        )
        return list(result.scalars().all())
