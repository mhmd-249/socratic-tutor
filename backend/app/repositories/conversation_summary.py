"""Conversation summary repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.conversation import Conversation
from app.models.conversation_summary import ConversationSummary
from app.repositories.base import BaseRepository


class ConversationSummaryRepository(BaseRepository[ConversationSummary]):
    """Repository for ConversationSummary model."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation summary repository."""
        super().__init__(ConversationSummary, session)

    async def get_by_conversation(
        self, conversation_id: UUID
    ) -> ConversationSummary | None:
        """
        Get summary for a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            ConversationSummary instance or None if not found
        """
        result = await self.session.execute(
            select(ConversationSummary).where(
                ConversationSummary.conversation_id == conversation_id
            )
        )
        return result.scalar_one_or_none()

    # Alias for consistency
    async def get_by_conversation_id(
        self, conversation_id: UUID
    ) -> ConversationSummary | None:
        """Alias for get_by_conversation."""
        return await self.get_by_conversation(conversation_id)

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[ConversationSummary]:
        """
        Get summaries for a user's conversations.

        Args:
            user_id: User UUID
            limit: Maximum number of summaries to return

        Returns:
            List of ConversationSummary instances
        """
        result = await self.session.execute(
            select(ConversationSummary)
            .join(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
