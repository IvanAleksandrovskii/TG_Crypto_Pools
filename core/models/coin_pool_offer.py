from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import UUID, ForeignKey, Float, Integer, Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base

if TYPE_CHECKING:
    from .coin import Coin
    from .pool import Pool
    from .chain import Chain


class CoinPoolOffer(Base):

    coin_id: Mapped[UUID] = mapped_column(ForeignKey("coins.id", ondelete="CASCADE"), nullable=False)
    coin: Mapped["Coin"] = relationship("Coin", back_populates="pools", lazy="joined")

    pool_id: Mapped[UUID] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False)
    pool: Mapped["Pool"] = relationship("Pool", back_populates="coin_pool_offers", lazy="joined")

    chain_id: Mapped[UUID] = mapped_column(ForeignKey("chains.id", ondelete="CASCADE"), nullable=False)
    chain: Mapped["Chain"] = relationship("Chain", lazy="joined")

    apr: Mapped[float] = mapped_column(Float, nullable=False)

    fee: Mapped[float] = mapped_column(Float, nullable=True)

    amount_from: Mapped[float] = mapped_column(Float, nullable=True)

    lock_period: Mapped[int] = mapped_column(Integer, nullable=False)  # days

    pool_share: Mapped[float] = mapped_column(Float, nullable=True)  # share in pool

    liquidity_token: Mapped[bool] = mapped_column(Boolean, default=False)  # does the liquidity token is in the offer
    liquidity_token_name: Mapped[str] = mapped_column(String, nullable=True)  # name of the liquidity token and other info if needed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    @validates('liquidity_token_name')
    def validate_liquidity_token_name(self, key, value):
        if value:
            setattr(self, 'liquidity_token', Boolean().python_type(True))
        return value

    def __repr__(self):
        return f"CoinPoolOffer(coin='{self.coin.name}', pool='{self.pool.name}', chain='{self.chain.name}', id={self.id})"

    def __str__(self):
        return f"(pool='{self.pool.name}', chain='{self.chain.name}', coin='{self.coin.name}', id={self.id})"
