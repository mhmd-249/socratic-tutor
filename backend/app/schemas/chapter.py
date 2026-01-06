"""Chapter schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChapterBase(BaseModel):
    """Base chapter schema with common attributes."""

    title: str
    chapter_number: int
    summary: str
    prerequisites: list[uuid.UUID] = []
    key_concepts: list[str] = []


class ChapterCreate(ChapterBase):
    """Schema for creating a new chapter."""

    book_id: uuid.UUID


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter."""

    title: str | None = None
    chapter_number: int | None = None
    summary: str | None = None
    prerequisites: list[uuid.UUID] | None = None
    key_concepts: list[str] | None = None


class ChapterResponse(ChapterBase):
    """Schema for chapter responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    book_id: uuid.UUID
    created_at: datetime
