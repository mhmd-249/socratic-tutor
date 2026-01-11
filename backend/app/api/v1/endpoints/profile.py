"""Learning profile endpoints."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.learning_profile import LearningProfile
from app.repositories.learning_profile import LearningProfileRepository
from app.repositories.chapter import ChapterRepository
from app.schemas.learning_profile import LearningProfileResponse
from app.schemas.chapter import ChapterResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=LearningProfileResponse)
async def get_learning_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LearningProfile:
    """
    Get the current user's learning profile.

    Creates a new profile if one doesn't exist.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User's learning profile
    """
    logger.info(f"User {current_user.id} requesting learning profile")

    profile_repo = LearningProfileRepository(db)
    profile = await profile_repo.get_by_user(current_user.id)

    if not profile:
        # Create new profile for user
        logger.info(f"Creating new learning profile for user {current_user.id}")
        profile_data = {
            "id": uuid.uuid4(),
            "user_id": current_user.id,
            "mastery_map": {},
            "identified_gaps": [],
            "strengths": [],
            "recommended_chapters": [],
            "total_study_time_minutes": 0,
            "updated_at": datetime.utcnow(),
        }
        profile = await profile_repo.create(profile_data)
        await db.commit()

    return profile


@router.get("/recommendations", response_model=list[ChapterResponse])
async def get_recommended_chapters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get recommended chapters for the current user based on their profile.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of recommended chapters
    """
    logger.info(f"User {current_user.id} requesting recommended chapters")

    profile_repo = LearningProfileRepository(db)
    chapter_repo = ChapterRepository(db)

    profile = await profile_repo.get_by_user(current_user.id)

    if not profile or not profile.recommended_chapters:
        logger.info(f"No recommendations for user {current_user.id}")
        return []

    # Fetch recommended chapters
    chapters = []
    for chapter_id in profile.recommended_chapters:
        chapter = await chapter_repo.get(chapter_id)
        if chapter:
            chapters.append(chapter)

    logger.info(f"Returning {len(chapters)} recommended chapters")
    return chapters
