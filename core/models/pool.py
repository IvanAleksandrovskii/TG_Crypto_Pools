from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_storages.integrations.sqlalchemy import FileType

from .base import Base
from .coin_pool_offer import CoinPoolOffer
from core import pool_storage


class Pool(Base):
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    logo = mapped_column(FileType(storage=pool_storage))

    coin_pool_offers: Mapped[List["CoinPoolOffer"]] = relationship(
        "CoinPoolOffer",
        back_populates="pool",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    website_url: Mapped[str] = mapped_column(String, nullable=True)

    # TODO: Add identification how (from where) offers for this pool are taken (like validator.info, defilama or etc.)
    parsing_source: Mapped[str] = mapped_column(String, nullable=True)

    def __repr__(self):
        return f"Pool(name='{self.name}', id={self.id})"

    def __str__(self):
        return f"{self.name}"
