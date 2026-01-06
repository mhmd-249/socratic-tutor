"""Conversation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.conversation import ConversationStatus


class ConversationBase(BaseModel):
    """Base conversation schema with common attributes."""

    pass


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""

    user_id: uuid.UUID
    chapter_id: uuid.UUID


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""

    status: ConversationStatus | None = None
    ended_at: datetime | None = None


class ConversationResponse(ConversationBase):
    """Schema for conversation responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    chapter_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    status: ConversationStatus
