"""Conversation summary model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConversationSummary(Base):
    """Conversation summary model for storing session analysis."""

    __tablename__ = "conversation_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text)
    topics_covered: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    concepts_understood: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )
    concepts_struggled: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="summary")

    def __repr__(self) -> str:
        """String representation of ConversationSummary."""
        return f"<ConversationSummary(id={self.id}, conversation_id={self.conversation_id})>"
