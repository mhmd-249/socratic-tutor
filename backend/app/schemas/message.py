"""Message schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.message import MessageRole


class MessageBase(BaseModel):
    """Base message schema with common attributes."""

    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a new message."""

    conversation_id: uuid.UUID


class MessageUpdate(BaseModel):
    """Schema for updating a message."""

    content: str | None = None


class MessageResponse(MessageBase):
    """Schema for message responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
