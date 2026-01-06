"""Learning profile schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LearningProfileBase(BaseModel):
    """Base learning profile schema with common attributes."""

    mastery_map: dict[str, Any] = {}
    identified_gaps: list[dict[str, Any]] = []
    strengths: list[str] = []
    recommended_chapters: list[uuid.UUID] = []
    total_study_time_minutes: int = 0


class LearningProfileCreate(LearningProfileBase):
    """Schema for creating a new learning profile."""

    user_id: uuid.UUID


class LearningProfileUpdate(BaseModel):
    """Schema for updating a learning profile."""

    mastery_map: dict[str, Any] | None = None
    identified_gaps: list[dict[str, Any]] | None = None
    strengths: list[str] | None = None
    recommended_chapters: list[uuid.UUID] | None = None
    total_study_time_minutes: int | None = None


class LearningProfileResponse(LearningProfileBase):
    """Schema for learning profile responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    updated_at: datetime
