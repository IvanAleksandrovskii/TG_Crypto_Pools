from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core import logger
from core.models import db_helper, Coin
from core.schemas import CoinResponse
from utils import Ordering

router = APIRouter()

coin_ordering = Ordering(Coin, ["name", "code", "id"], default_field="name")


@router.get("/", response_model=List[CoinResponse])
async def get_all_coins(
    session: AsyncSession = Depends(db_helper.session_getter),
    order: Optional[str] = Query(None, description="Order by field"),
    order_desc: Optional[bool] = Query(None, description="Order in descending order")
):
    query = Coin.active().order_by(coin_ordering.order_by(order, order_desc))
    try:
        result = await session.execute(query)
        coins = result.scalars().all()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_coins: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [CoinResponse.model_validate(coin) for coin in coins]


@router.get("/{coin_id}", response_model=CoinResponse)
async def get_coin_by_id(
        coin_id: UUID,
        session: AsyncSession = Depends(db_helper.session_getter)
):
    query = Coin.active().where(Coin.id == coin_id)
    try:
        result = await session.execute(query)
        chain = result.scalars().one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_coin_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not chain:
        raise HTTPException(status_code=404, detail="Coin not found")

    return CoinResponse.model_validate(chain)
