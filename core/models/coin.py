from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_storages.integrations.sqlalchemy import FileType

from .base import Base
from .coin_chain_association import coin_chain
from core import coin_storage

if TYPE_CHECKING:
    from .chain import Chain
    from .coin_pool_offer import CoinPoolOffer


class Coin(Base):
    name: Mapped[str] = mapped_column(String, nullable=True)

    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    logo = mapped_column(FileType(storage=coin_storage))

    chains: Mapped[List["Chain"]] = relationship(
        "Chain",
        secondary=coin_chain,
        back_populates="coins",
        lazy="selectin",
        cascade="save-update, merge",
    )
    pools: Mapped[List["CoinPoolOffer"]] = relationship(
        "CoinPoolOffer",
        back_populates="coin",
        lazy="selectin",
        cascade="save-update, merge, delete, delete-orphan",
    )

    def __repr__(self):
        return f"Coin(name='{self.name}', code='{self.code}', id={self.id})"

    def __str__(self):
        return f"{self.name} ({self.code})"
