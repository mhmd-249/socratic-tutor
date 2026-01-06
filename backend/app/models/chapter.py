"""Chapter model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Chapter(Base):
    """Chapter model representing book chapters."""

    __tablename__ = "chapters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    prerequisites: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )
    key_concepts: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    book: Mapped["Book"] = relationship(back_populates="chapters")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Chapter."""
        return f"<Chapter(id={self.id}, title={self.title})>"
