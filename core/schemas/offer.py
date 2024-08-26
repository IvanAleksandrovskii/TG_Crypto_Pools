from datetime import datetime
from pydantic import Field

from .base import BaseResponse
from .chain import ChainResponse
from .coin import CoinResponse
from .pool import PoolResponse


class OfferResponse(BaseResponse):
    pool: PoolResponse
    chain: ChainResponse
    coin: CoinResponse

    apr: float = Field(ge=0, le=100)
    amount_from: float = Field(ge=0)
    lock_period: int = Field(ge=0)
    pool_share: float = Field(ge=0, le=100)
    liquidity_token: bool
    liquidity_token_name: str

    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,

            coin=CoinResponse.model_validate(obj.coin),
            pool=PoolResponse.model_validate(obj.pool),
            chain=ChainResponse.model_validate(obj.chain),

            apr=obj.apr,
            amount_from=obj.amount_from,
            lock_period=obj.lock_period,
            pool_share=obj.pool_share,
            liquidity_token=obj.liquidity_token,
            liquidity_token_name=obj.liquidity_token_name,
            created_at=obj.created_at
        )
