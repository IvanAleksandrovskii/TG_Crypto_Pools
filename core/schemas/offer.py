from datetime import datetime
from typing import Optional, List
from pydantic import Field
from .base import BaseResponse
from .chain import ChainResponse
from .coin import CoinResponse
from .pool import PoolResponse


class OfferResponse(BaseResponse):
    pool: PoolResponse
    chain: ChainResponse
    coin: CoinResponse
    apr: Optional[float] = Field(ge=0, le=100)
    fee: Optional[float] = Field(ge=0, le=100)
    amount_from: Optional[float] = Field(ge=0)
    lock_period: Optional[int] = Field(ge=0)
    pool_share: Optional[float] = Field(ge=0, le=100)
    liquidity_token: bool
    liquidity_token_name: Optional[str]
    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            coin=CoinResponse.model_validate(obj.coin),
            pool=PoolResponse.model_validate(obj.pool),
            chain=ChainResponse.model_validate(obj.chain),
            apr=obj.apr,
            fee=obj.fee,
            amount_from=obj.amount_from,
            lock_period=obj.lock_period,
            pool_share=obj.pool_share,
            liquidity_token=obj.liquidity_token,
            liquidity_token_name=obj.liquidity_token_name,
            created_at=obj.created_at,
        )


class OfferHistory(BaseResponse):
    apr: float
    amount_from: Optional[float]
    pool_share: Optional[float]
    created_at: datetime
    historical_coin_price: Optional[float] = Field(None, description="Coin price at the time of offer creation")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            apr=obj.apr,
            amount_from=obj.amount_from,
            pool_share=obj.pool_share,
            created_at=obj.created_at,
            historical_coin_price=obj.historical_coin_price if hasattr(obj, 'historical_coin_price') else None
        )


class OfferResponseWithHistory(BaseResponse):
    pool: PoolResponse
    chain: ChainResponse
    coin: CoinResponse
    lock_period: int
    liquidity_token: bool
    liquidity_token_name: Optional[str]
    history: List[OfferHistory]

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            pool=PoolResponse.model_validate(obj.pool),
            chain=ChainResponse.model_validate(obj.chain),
            coin=CoinResponse.model_validate(obj.coin),
            lock_period=obj.lock_period,
            liquidity_token=obj.liquidity_token,
            liquidity_token_name=obj.liquidity_token_name,
            history=[OfferHistory.model_validate(h) for h in obj.history]
        )
