from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .coin_chain_pool_associations import coin_chain

if TYPE_CHECKING:
    from .coin import Coin


class Chain(Base):
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    coins: Mapped[List["Coin"]] = relationship(
        "Coin",
        secondary=coin_chain,
        back_populates="chains",
        lazy="selectin",
    )