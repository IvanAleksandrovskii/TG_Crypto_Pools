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
    from .coin_price import CoinPrice


class Coin(Base):
    name: Mapped[str] = mapped_column(String, nullable=True)

    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    logo = mapped_column(FileType(storage=coin_storage))

    coin_id_for_price_getter: Mapped[String] = mapped_column(String, nullable=True)

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
        lazy="noload",
        cascade="save-update, merge, delete, delete-orphan",
    )
    prices: Mapped[List["CoinPrice"]] = relationship(
        "CoinPrice",
        back_populates="coin",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="desc(CoinPrice.created_at)",
    )

    @property
    def latest_price(self):
        return self.prices[0] if self.prices else None

    def __repr__(self):
        return f"Coin(name='{self.name}', code='{self.code}', id={self.id})"

    def __str__(self):
        return f"{self.code}"
