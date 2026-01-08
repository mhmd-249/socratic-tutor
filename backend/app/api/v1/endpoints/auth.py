"""Authentication endpoints."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.learning_profile import LearningProfileRepository
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class AuthCallbackRequest(BaseModel):
    """Request body for auth callback."""

    supabase_id: str
    email: EmailStr
    name: str


@router.post("/callback", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def auth_callback(
    request: AuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Handle Supabase authentication callback.

    Creates or updates user in our database after Supabase authentication.

    Args:
        request: Auth callback data from Supabase
        db: Database session

    Returns:
        UserResponse: Created or updated user
    """
    try:
        logger.info(f"Auth callback for supabase_id: {request.supabase_id}")

        user_repo = UserRepository(db)
        learning_profile_repo = LearningProfileRepository(db)

        # Check if user already exists
        existing_user = await user_repo.get_by_supabase_id(request.supabase_id)

        if existing_user:
            logger.info(f"Updating existing user: {existing_user.id}")
            # Update existing user if email or name changed
            updated_user = await user_repo.update(
                existing_user.id,
                {
                    "email": request.email,
                    "name": request.name,
                },
            )
            await db.commit()
            return updated_user

        # Create new user
        logger.info(f"Creating new user with email: {request.email}")
        user_data = {
            "id": uuid.uuid4(),
            "supabase_id": request.supabase_id,
            "email": request.email,
            "name": request.name,
            "created_at": datetime.utcnow(),
        }
        new_user = await user_repo.create(user_data)

        # Create learning profile for new user
        logger.info(f"Creating learning profile for user: {new_user.id}")
        profile_data = {
            "id": uuid.uuid4(),
            "user_id": new_user.id,
            "mastery_map": {},
            "identified_gaps": [],
            "strengths": [],
            "recommended_chapters": [],
            "total_study_time_minutes": 0,
            "updated_at": datetime.utcnow(),
        }
        await learning_profile_repo.create(profile_data)

        await db.commit()
        logger.info(f"Successfully created user and profile: {new_user.id}")

        return new_user

    except Exception as e:
        logger.error(f"Error in auth callback: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to process authentication callback",
                "code": "AUTH_CALLBACK_ERROR",
                "error": str(e),
            },
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user from JWT

    Returns:
        UserResponse: Current user profile
    """
    return current_user
