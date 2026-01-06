"""Chunk schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChunkBase(BaseModel):
    """Base chunk schema with common attributes."""

    content: str
    chunk_index: int
    section_title: str | None = None
    chunk_metadata: dict[str, Any] = {}


class ChunkCreate(ChunkBase):
    """Schema for creating a new chunk."""

    chapter_id: uuid.UUID
    embedding: list[float]


class ChunkUpdate(BaseModel):
    """Schema for updating a chunk."""

    content: str | None = None
    embedding: list[float] | None = None
    chunk_index: int | None = None
    section_title: str | None = None
    chunk_metadata: dict[str, Any] | None = None


class ChunkResponse(ChunkBase):
    """Schema for chunk responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chapter_id: uuid.UUID
    created_at: datetime


class ChunkWithEmbedding(ChunkResponse):
    """Schema for chunk with embedding included."""

    embedding: list[float]
