from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .coin_pool_offer import CoinPoolOffer


class Pool(Base):
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    coin_pool_offers: Mapped[List["CoinPoolOffer"]] = relationship(
        "CoinPoolOffer",
        back_populates="pool",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    website_url: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"Pool(name='{self.name}', id={self.id})"

    def __str__(self):
        return f"{self.name}"
