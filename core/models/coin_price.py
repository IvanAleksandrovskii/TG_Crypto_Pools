from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import Float, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base

if TYPE_CHECKING:
    from .coin import Coin


class CoinPrice(Base):
    coin_id: Mapped[UUID] = mapped_column(ForeignKey("coins.id", ondelete="CASCADE"), nullable=False)
    coin: Mapped["Coin"] = relationship("Coin", back_populates="prices")

    price: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self):
        return f"CoinPrice(coin_id={self.coin_id}, price={self.price}, created_at={self.created_at})"

    def __str__(self):
        return f"Price: {self.price} at {self.created_at}"
