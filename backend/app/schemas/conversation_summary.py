"""Conversation summary schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationSummaryBase(BaseModel):
    """Base conversation summary schema with common attributes."""

    summary: str
    topics_covered: list[str] = []
    concepts_understood: list[str] = []
    concepts_struggled: list[str] = []
    questions_asked: int = 0
    engagement_score: float = 0.0


class ConversationSummaryCreate(ConversationSummaryBase):
    """Schema for creating a new conversation summary."""

    conversation_id: uuid.UUID


class ConversationSummaryUpdate(BaseModel):
    """Schema for updating a conversation summary."""

    summary: str | None = None
    topics_covered: list[str] | None = None
    concepts_understood: list[str] | None = None
    concepts_struggled: list[str] | None = None
    questions_asked: int | None = None
    engagement_score: float | None = None


class ConversationSummaryResponse(ConversationSummaryBase):
    """Schema for conversation summary responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
