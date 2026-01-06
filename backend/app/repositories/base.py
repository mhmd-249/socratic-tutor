"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar, Type, Any
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        """
        Get a record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Dictionary of model attributes

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self, id: UUID, obj_in: dict[str, Any]
    ) -> ModelType | None:
        """
        Update a record.

        Args:
            id: Record UUID
            obj_in: Dictionary of attributes to update

        Returns:
            Updated model instance or None if not found
        """
        # Filter out None values
        update_data = {k: v for k, v in obj_in.items() if v is not None}

        if not update_data:
            return await self.get(id)

        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**update_data)
        )
        await self.session.flush()
        return await self.get(id)

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
