from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .coin_pool_offer import CoinPoolOffer


class Pool(Base):
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    coin_pool_offers: Mapped[List["CoinPoolOffer"]] = relationship("CoinPoolOffer", back_populates="pool",
                                                                   lazy="selectin")
    website_url: Mapped[str] = mapped_column(String, nullable=False)