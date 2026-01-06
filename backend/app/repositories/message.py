"""Message repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message model."""

    def __init__(self, session: AsyncSession):
        """Initialize message repository."""
        super().__init__(Message, session)

    async def get_by_conversation(
        self, conversation_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Message]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: Conversation UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of messages ordered by created_at
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
