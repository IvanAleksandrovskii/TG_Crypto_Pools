from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core import logger
from core.models import db_helper, Coin
from core.schemas import CoinResponse

router = APIRouter()


@router.get("/", response_model=List[CoinResponse])
async def get_all_coins(
    session: AsyncSession = Depends(db_helper.session_getter)
):
    query = Coin.active()
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
