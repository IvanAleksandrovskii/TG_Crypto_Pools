from typing import List, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_storages.integrations.sqlalchemy import FileType

from .base import Base
from .coin_chain_association import coin_chain
from core import chain_storage

if TYPE_CHECKING:
    from .coin import Coin


class Chain(Base):
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    logo = mapped_column(FileType(storage=chain_storage))

    coins: Mapped[List["Coin"]] = relationship(
        "Coin",
        secondary=coin_chain,
        back_populates="chains",
        lazy="selectin",
    )

    def __repr__(self):
        return f"Chain(name='{self.name}', id={self.id})"

    def __str__(self):
        return f"{self.name}"
