import uuid

from sqlalchemy import MetaData, text, Boolean, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

from core import settings
from utils import camel_case_to_snake_case


metadata = MetaData(naming_convention=settings.db.naming_convention)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models in the project.
    Provides common attributes and methods for all models.
    """
    __abstract__ = True
    metadata = metadata

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Automatically generates table name from the class name.
        Converts CamelCase to snake_case and adds 's' at the end.
        """
        return f"{camel_case_to_snake_case(cls.__name__)}s"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @classmethod
    def active(cls):
        """
        Returns a query that filters only active objects.
        This method should be used as the base for all queries.
        """
        return select(cls).where(cls.is_active == True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id})"
