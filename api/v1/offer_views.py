from datetime import datetime, timedelta, UTC
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
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


@router.get("/{offer_id}", response_model=List[OfferResponse])
async def get_offer_by_id(
    offer_id: UUID,
    days: Optional[int] = Query(default=None, ge=1, description="Number of days to fetch history"),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        # Base query first
        base_query = (
            select(CoinPoolOffer)
            .options(
                joinedload(CoinPoolOffer.coin),
                joinedload(CoinPoolOffer.pool),
                joinedload(CoinPoolOffer.chain)
            )
            .join(CoinPoolOffer.pool)
            .join(CoinPoolOffer.coin)
            .join(CoinPoolOffer.chain)
            .where(CoinPoolOffer.is_active == True)
            .where(Pool.is_active == True)
            .where(Coin.is_active == True)
            .where(Chain.is_active == True)
            .filter(CoinPoolOffer.id == offer_id)
        )
        result = await session.execute(base_query)
        base_offer = result.unique().scalar_one_or_none()

        if not base_offer:
            raise HTTPException(status_code=404, detail="Offer not found")

        # if
        if days is None:
            return [OfferResponse.model_validate(base_offer)]

        # If days is not None, get the offer history
        common_filter = and_(
            CoinPoolOffer.coin_id == base_offer.coin_id,
            CoinPoolOffer.pool_id == base_offer.pool_id,
            CoinPoolOffer.chain_id == base_offer.chain_id,
            CoinPoolOffer.lock_period == base_offer.lock_period
        )

        start_date = datetime.now(UTC) - timedelta(days=days)

        query = (
            select(CoinPoolOffer)
            .options(
                joinedload(CoinPoolOffer.coin),
                joinedload(CoinPoolOffer.pool),
                joinedload(CoinPoolOffer.chain)
            )
            .filter(
                common_filter,
                CoinPoolOffer.created_at >= start_date,
                # TODO: IT'S A REPEAT CODE, KEEPING FOR DOUBLE CHECKING PURPOSE
                CoinPoolOffer.is_active == True,
                Coin.is_active == True,
                Pool.is_active == True,
                Chain.is_active == True
            )
            .order_by(CoinPoolOffer.created_at.desc())
        )
        result = await session.execute(query)
        offers = result.unique().scalars().all()

        # If no offers found in the specified period, return the base_offer
        if not offers:
            return [OfferResponse.model_validate(base_offer)]

        # If offers found in the specified period, return the offers
        return [OfferResponse.model_validate(offer) for offer in offers]

    except SQLAlchemyError as e:
        logger.exception(f"Database error occurred in get_offer_by_id: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error occurred in get_offer_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
