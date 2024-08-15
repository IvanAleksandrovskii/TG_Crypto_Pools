from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .coin import Coin
    from .pool import Pool
    from .chain import Chain


# TODO: After I understand what does "доли в пуле" mean add this field
class CoinPoolOffer(Base):
    coin_id: Mapped[UUID] = mapped_column(ForeignKey("coins.id"), nullable=False)
    coin: Mapped["Coin"] = relationship("Coin", back_populates="pools", lazy="joined")

    pool_id: Mapped[UUID] = mapped_column(ForeignKey("pools.id"), nullable=False)
    pool: Mapped["Pool"] = relationship("Pool", back_populates="coin_pool_offers", lazy="joined")

    chain_id: Mapped[UUID] = mapped_column(ForeignKey("chains.id"), nullable=False)
    chain: Mapped["Chain"] = relationship("Chain", lazy="joined")

    apr_from: Mapped[float] = mapped_column(Float, nullable=False)
    apr_to: Mapped[float] = mapped_column(Float, nullable=False)
    current_rate: Mapped[float] = mapped_column(Float, nullable=False)

    amount_from: Mapped[float] = mapped_column(Float, nullable=False)
    amount_to: Mapped[float] = mapped_column(Float, nullable=False)

    time_delta_from: Mapped[int] = mapped_column(Integer, nullable=False)  # days
    time_delta_to: Mapped[int] = mapped_column(Integer, nullable=False)  # days

    pool_share: Mapped[float] = mapped_column(Float, nullable=False)  # share in pool
    previous_rate: Mapped[float] = mapped_column(Float)  # previous rate in pool
    liquidity_token: Mapped[bool] = mapped_column(Boolean, default=False)  # token liquidity
