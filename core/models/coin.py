from typing import List, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .coin_chain_pool_associations import coin_chain

if TYPE_CHECKING:
    from .chain import Chain
    from .coin_pool_offer import CoinPoolOffer


class Coin(Base):
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    chains: Mapped[List["Chain"]] = relationship(
        "Chain",
        secondary=coin_chain,
        back_populates="coins",
        lazy="selectin",
    )
    pools: Mapped[List["CoinPoolOffer"]] = relationship(
        "CoinPoolOffer",
        back_populates="coin",
        lazy="selectin"
    )

    @hybrid_property
    def max_apr(self) -> float:
        return max((pool.apr_to for pool in self.pools), default=0)

    @hybrid_property
    def min_amount(self) -> float:
        return min((pool.amount_from for pool in self.pools), default=0)

    @hybrid_property
    def min_lock_period(self) -> int:
        return min((pool.time_delta_from for pool in self.pools), default=0)