"""User schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a new user."""

    supabase_id: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    name: str | None = None


class UserResponse(UserBase):
    """Schema for user responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supabase_id: str
    created_at: datetime
