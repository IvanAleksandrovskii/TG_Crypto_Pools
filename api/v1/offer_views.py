from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core import logger
from core.models import db_helper, CoinPoolOffer, Coin, Pool, Chain
from core.schemas import OfferResponse

router = APIRouter()


async def get_latest_offers(session: AsyncSession):
    subquery = (
        select(
            CoinPoolOffer.coin_id,
            CoinPoolOffer.pool_id,
            CoinPoolOffer.chain_id,
            CoinPoolOffer.lock_period,
            func.max(CoinPoolOffer.created_at).label("max_created_at")  # filters latest created_at
        )
        .group_by(
            CoinPoolOffer.coin_id,
            CoinPoolOffer.pool_id,
            CoinPoolOffer.chain_id,
            CoinPoolOffer.lock_period
        )
        .subquery()
    )

    query = (
        select(CoinPoolOffer)
        .join(
            subquery,
            (CoinPoolOffer.coin_id == subquery.c.coin_id) &
            (CoinPoolOffer.pool_id == subquery.c.pool_id) &
            (CoinPoolOffer.chain_id == subquery.c.chain_id) &
            (CoinPoolOffer.lock_period == subquery.c.lock_period) &
            (CoinPoolOffer.created_at == subquery.c.max_created_at)
        )
        .options(
            joinedload(CoinPoolOffer.coin),
            joinedload(CoinPoolOffer.pool),
            joinedload(CoinPoolOffer.chain)
        )
        .join(Coin, CoinPoolOffer.coin_id == Coin.id)
        .join(Pool, CoinPoolOffer.pool_id == Pool.id)
        .join(Chain, CoinPoolOffer.chain_id == Chain.id)
        .filter(
            CoinPoolOffer.is_active == True,
            Coin.is_active == True,
            Pool.is_active == True,
            Chain.is_active == True
        )
    )

    return query


@router.get("/", response_model=List[OfferResponse])
async def get_all_offers(
    session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        query = await get_latest_offers(session)
        result = await session.execute(query)
        offers = result.unique().scalars().all()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_offers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [OfferResponse.model_validate(offer) for offer in offers]


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer_by_id(
    offer_id: UUID,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        query = (
            select(CoinPoolOffer)
            .options(
                joinedload(CoinPoolOffer.coin),
                joinedload(CoinPoolOffer.pool),
                joinedload(CoinPoolOffer.chain)
            )
            .join(Coin, CoinPoolOffer.coin_id == Coin.id)
            .join(Pool, CoinPoolOffer.pool_id == Pool.id)
            .join(Chain, CoinPoolOffer.chain_id == Chain.id)
            .filter(
                CoinPoolOffer.id == offer_id,
                CoinPoolOffer.is_active == True,
                Coin.is_active == True,
                Pool.is_active == True,
                Chain.is_active == True
            )
        )
        result = await session.execute(query)
        offer = result.unique().scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_offer_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    return OfferResponse.model_validate(offer)
