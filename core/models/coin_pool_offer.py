from typing import TYPE_CHECKING
from sqlalchemy import UUID, ForeignKey, Float, Integer, Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .coin import Coin
    from .pool import Pool
    from .chain import Chain


class CoinPoolOffer(Base):
    __table_args__ = (
        UniqueConstraint('pool_id', 'chain_id', 'coin_id', name='uq_pool_chain_coin'),
    )

    coin_id: Mapped[UUID] = mapped_column(ForeignKey("coins.id"), nullable=False)
    coin: Mapped["Coin"] = relationship("Coin", back_populates="pools", lazy="joined")  # coin with can_delete=False

    pool_id: Mapped[UUID] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False)
    pool: Mapped["Pool"] = relationship("Pool", back_populates="coin_pool_offers", lazy="joined")

    chain_id: Mapped[UUID] = mapped_column(ForeignKey("chains.id"), nullable=False)
    chain: Mapped["Chain"] = relationship("Chain", lazy="joined")  # chain with can_delete=False

    apr: Mapped[float] = mapped_column(Float, nullable=False)
    previous_apr: Mapped[float] = mapped_column(Float, nullable=True)

    amount_from: Mapped[float] = mapped_column(Float, nullable=False)

    lock_period: Mapped[int] = mapped_column(Integer, nullable=False)  # days

    pool_share: Mapped[float] = mapped_column(Float, nullable=False)  # share in pool

    liquidity_token: Mapped[bool] = mapped_column(Boolean, default=False)  # token liquidity
    liquidity_token_name: Mapped[str] = mapped_column(String, nullable=True)  # name of the liquidity token and other info if needed

    def __repr__(self):
        return f"CoinPoolOffer(coin='{self.coin.name}', pool='{self.pool.name}', chain='{self.chain.name}', id={self.id})"

    def __str__(self):
        return f"(pool='{self.pool.name}', chain='{self.chain.name}', coin='{self.coin.name}', id={self.id})"
