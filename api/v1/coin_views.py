from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import logger
from core.models import db_helper, Coin, CoinPrice, Chain, coin_chain
from core.schemas import CoinResponse
from utils import Ordering

router = APIRouter()

coin_ordering = Ordering(Coin, ["name", "code", "id"], default_field="name")


@router.get("/", response_model=List[CoinResponse])
async def get_all_coins(
        session: AsyncSession = Depends(db_helper.session_getter),
        order: Optional[str] = Query(None, description="Order by field"),
        order_desc: Optional[bool] = Query(None, description="Order in descending order"),
        chain_id: Optional[uuid.UUID] = Query(None, description="Filter by chain ID")
):
    try:
        # Subquery to get latest prices
        latest_price_subquery = (
            select(CoinPrice.coin_id, func.max(CoinPrice.created_at).label('max_date'))
            .group_by(CoinPrice.coin_id)
            .subquery()
        )

        # Main query
        query = (
            select(Coin, CoinPrice)
            .outerjoin(latest_price_subquery, Coin.id == latest_price_subquery.c.coin_id)
            .outerjoin(CoinPrice, (CoinPrice.coin_id == Coin.id) &
                       (CoinPrice.created_at == latest_price_subquery.c.max_date))
            .where(Coin.is_active == True)
        )

        # Apply chain filter if provided
        if chain_id:
            query = (
                query
                .join(coin_chain)
                .join(Chain)
                .where(Chain.id == chain_id)
            )

        query = (
            query
            .options(selectinload(Coin.prices))
            .order_by(coin_ordering.order_by(order, order_desc))
        )

        result = await session.execute(query)
        coins_with_prices = result.unique().all()

        return [
            CoinResponse.model_validate(
                coin,
                update={'current_price': price.price if price else None}
            ) for coin, price in coins_with_prices
        ]

    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_coins: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{coin_id}", response_model=CoinResponse)
async def get_coin_by_id(
        coin_id: uuid.UUID,
        session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        query = (
            select(Coin, CoinPrice)
            .outerjoin(CoinPrice, Coin.id == CoinPrice.coin_id)
            .options(selectinload(Coin.prices))
            .where(Coin.id == coin_id, Coin.is_active == True)
            .order_by(CoinPrice.created_at.desc())
            .limit(1)
        )

        result = await session.execute(query)
        coin_with_price = result.first()

        if not coin_with_price:
            raise HTTPException(status_code=404, detail="Coin not found")

        coin, price = coin_with_price
        return CoinResponse.model_validate(
            coin,
            update={'current_price': price.price if price else None}
        )

    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_coin_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
