"""Conversation repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationStatus
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation model."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation repository."""
        super().__init__(Conversation, session)

    async def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Conversation]:
        """
        Get all conversations for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations ordered by started_at (newest first)
        """
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_chapter(
        self, chapter_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Conversation]:
        """
        Get all conversations for a chapter.

        Args:
            chapter_id: Chapter UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations
        """
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.chapter_id == chapter_id)
            .order_by(Conversation.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_by_user(self, user_id: UUID) -> list[Conversation]:
        """
        Get all active conversations for a user.

        Args:
            user_id: User UUID

        Returns:
            List of active conversations
        """
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.status == ConversationStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())
