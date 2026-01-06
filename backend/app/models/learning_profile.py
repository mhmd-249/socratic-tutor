"""Learning profile model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningProfile(Base):
    """Learning profile model tracking student progress and gaps."""

    __tablename__ = "learning_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    mastery_map: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"chapter_id": {"score": 0.8, "last_studied": "..."}}
    identified_gaps: Mapped[list[dict]] = mapped_column(
        JSONB, default=list
    )  # [{"concept": "...", "severity": "high", "related_chapters": [...]}]
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    recommended_chapters: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )
    total_study_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="learning_profile")

    def __repr__(self) -> str:
        """String representation of LearningProfile."""
        return f"<LearningProfile(id={self.id}, user_id={self.user_id})>"
