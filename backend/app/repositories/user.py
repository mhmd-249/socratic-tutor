"""User repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_supabase_id(self, supabase_id: str) -> User | None:
        """
        Get user by Supabase ID.

        Args:
            supabase_id: Supabase user ID

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.supabase_id == supabase_id)
        )
        return result.scalar_one_or_none()
