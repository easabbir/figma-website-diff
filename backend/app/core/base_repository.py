"""Base repository class to reduce redundant code."""

from sqlalchemy.orm import Session
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get a record by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination."""
        return self.db.query(self.model).offset(offset).limit(limit).all()

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """Update a record."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelType) -> bool:
        """Delete a record."""
        try:
            self.db.delete(instance)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            self.db.rollback()
            return False

    def delete_by_id(self, id: Any) -> bool:
        """Delete a record by ID."""
        instance = self.get_by_id(id)
        if instance:
            return self.delete(instance)
        return False

    def count(self) -> int:
        """Count total records."""
        return self.db.query(self.model).count()

    def exists(self, **filters) -> bool:
        """Check if a record exists with given filters."""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None
