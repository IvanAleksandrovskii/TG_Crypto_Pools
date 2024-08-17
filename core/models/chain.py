from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .coin_chain_association import coin_chain

if TYPE_CHECKING:
    from .coin import Coin


# TODO: no_delete logic (?) now in admin can_delete=False
class Chain(Base):
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
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
