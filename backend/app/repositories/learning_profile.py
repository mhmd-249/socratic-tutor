"""Learning profile repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_profile import LearningProfile
from app.repositories.base import BaseRepository


class LearningProfileRepository(BaseRepository[LearningProfile]):
    """Repository for LearningProfile model."""

    def __init__(self, session: AsyncSession):
        """Initialize learning profile repository."""
        super().__init__(LearningProfile, session)

    async def get_by_user(self, user_id: UUID) -> LearningProfile | None:
        """
        Get learning profile for a user.

        Args:
            user_id: User UUID

        Returns:
            LearningProfile instance or None if not found
        """
        result = await self.session.execute(
            select(LearningProfile).where(LearningProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
