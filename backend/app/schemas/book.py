"""Book schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookBase(BaseModel):
    """Base book schema with common attributes."""

    title: str
    author: str
    description: str


class BookCreate(BookBase):
    """Schema for creating a new book."""

    pass


class BookUpdate(BaseModel):
    """Schema for updating a book."""

    title: str | None = None
    author: str | None = None
    description: str | None = None


class BookResponse(BookBase):
    """Schema for book responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
