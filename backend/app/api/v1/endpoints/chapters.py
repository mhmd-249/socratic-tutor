"""Chapter endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chapter import Chapter
from app.repositories.chapter import ChapterRepository
from app.schemas.chapter import ChapterResponse, ChapterWithBookResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[ChapterWithBookResponse])
async def list_chapters(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    book_id: UUID | None = Query(None, description="Filter by book ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Chapter]:
    """
    List all chapters with their book information.

    Optionally filter by book_id.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        book_id: Optional book ID to filter chapters
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of chapters with book information
    """
    logger.info(f"User {current_user.id} listing chapters (skip={skip}, limit={limit})")

    chapter_repo = ChapterRepository(db)

    if book_id:
        # Filter by book
        chapters = await chapter_repo.get_by_book(book_id)
        # Apply pagination manually for filtered results
        chapters = chapters[skip : skip + limit]
    else:
        # Get all chapters with books
        chapters = await chapter_repo.get_all_with_books(skip=skip, limit=limit)

    logger.info(f"Returning {len(chapters)} chapters")
    return chapters


@router.get("/{chapter_id}", response_model=ChapterWithBookResponse)
async def get_chapter(
    chapter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Chapter:
    """
    Get a single chapter by ID with book information.

    Args:
        chapter_id: Chapter UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Chapter with book information

    Raises:
        HTTPException: If chapter not found
    """
    logger.info(f"User {current_user.id} requesting chapter {chapter_id}")

    chapter_repo = ChapterRepository(db)
    chapter = await chapter_repo.get_with_book(chapter_id)

    if not chapter:
        logger.warning(f"Chapter {chapter_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Chapter not found", "code": "CHAPTER_NOT_FOUND"},
        )

    return chapter
