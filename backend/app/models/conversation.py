"""Conversation model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConversationStatus(str, Enum):
    """Conversation status enumeration."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Conversation(Base):
    """Conversation model representing chat sessions."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[ConversationStatus] = mapped_column(
        SQLEnum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    chapter: Mapped["Chapter"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    summary: Mapped["ConversationSummary"] = relationship(
        back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Conversation."""
        return f"<Conversation(id={self.id}, user_id={self.user_id}, status={self.status})>"
