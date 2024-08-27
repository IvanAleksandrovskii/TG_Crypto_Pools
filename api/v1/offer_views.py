from datetime import datetime, timedelta, UTC
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core import logger
from core.models import db_helper, CoinPoolOffer, Coin, Pool, Chain
from core.schemas import OfferResponse
from utils import Ordering

router = APIRouter()

offer_ordering = Ordering(CoinPoolOffer,
                          [
                              "lock_period", "apr", "created_at", "amount_from",
                              "pool_share", "liquidity_token", "liquidity_token_name",
                              "coin.name", "pool.name", "chain.name", "id",
                          ],
                          default_field="id")


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
        CoinPoolOffer.active()
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
        coin_id: Optional[UUID] = Query(None, description="Filter by coin ID"),
        chain_id: Optional[UUID] = Query(None, description="Filter by chain ID"),
        pool_id: Optional[UUID] = Query(None, description="Filter by pool ID"),
        session: AsyncSession = Depends(db_helper.session_getter),
        order: Optional[str] = Query(None, description="Order by field"),
        order_desc: Optional[bool] = Query(None, description="Order in descending order")
):
    try:
        query = await get_latest_offers(session)

        # Apply filters based on provided query parameters
        if coin_id:
            query = query.filter(CoinPoolOffer.coin_id == coin_id)
        if chain_id:
            query = query.filter(CoinPoolOffer.chain_id == chain_id)
        if pool_id:
            query = query.filter(CoinPoolOffer.pool_id == pool_id)

        # Apply ordering
        query = query.order_by(offer_ordering.order_by(order, order_desc))

        result = await session.execute(query)
        offers = result.unique().scalars().all()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_offers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [OfferResponse.model_validate(offer) for offer in offers]


@router.get("/{offer_id}", response_model=List[OfferResponse])  # One and history
async def get_offer_by_id(
        offer_id: UUID,
        days: Optional[int] = Query(default=None, ge=1, description="Number of days to fetch history"),
        session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        # Base query first
        base_query = (
            CoinPoolOffer.active()
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
        logger.debug(f"Executing query for offer_id: {offer_id}")
        result = await session.execute(base_query)
        base_offer = result.unique().scalar_one_or_none()
        logger.debug(f"Query result: {base_offer}")

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
            CoinPoolOffer.active()
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

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception(f"Database error occurred in get_offer_by_id: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error occurred in get_offer_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/max-apr/{coin_id}", response_model=OfferResponse)
async def get_max_apr_offer(
    coin_id: UUID,
    chain_id: Optional[UUID] = Query(None, description="Filter by chain ID"),
    pool_id: Optional[UUID] = Query(None, description="Filter by pool ID"),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    try:
        # Subquery for  coin, pool, chain
        latest_offers_subquery = (
            select(
                CoinPoolOffer.coin_id,
                CoinPoolOffer.pool_id,
                CoinPoolOffer.chain_id,
                CoinPoolOffer.lock_period,
                func.max(CoinPoolOffer.created_at).label("max_created_at")
            )
            .group_by(
                CoinPoolOffer.coin_id,
                CoinPoolOffer.pool_id,
                CoinPoolOffer.chain_id,
                CoinPoolOffer.lock_period
            )
            .subquery()
        )

        # Main query
        query = (
            select(CoinPoolOffer)
            .join(
                latest_offers_subquery,
                and_(
                    CoinPoolOffer.coin_id == latest_offers_subquery.c.coin_id,
                    CoinPoolOffer.pool_id == latest_offers_subquery.c.pool_id,
                    CoinPoolOffer.chain_id == latest_offers_subquery.c.chain_id,
                    CoinPoolOffer.lock_period == latest_offers_subquery.c.lock_period,
                    CoinPoolOffer.created_at == latest_offers_subquery.c.max_created_at
                )
            )
            .options(
                joinedload(CoinPoolOffer.coin),
                joinedload(CoinPoolOffer.pool),
                joinedload(CoinPoolOffer.chain)
            )
            .join(Coin)
            .join(Pool)
            .join(Chain)
            .filter(CoinPoolOffer.coin_id == coin_id)
            .filter(CoinPoolOffer.is_active == True)
            .filter(Coin.is_active == True)
            .filter(Pool.is_active == True)
            .filter(Chain.is_active == True)
        )

        # Add filters based on provided query parameters
        if chain_id:
            query = query.filter(CoinPoolOffer.chain_id == chain_id)
        if pool_id:
            query = query.filter(CoinPoolOffer.pool_id == pool_id)

        # Sort by APR descending
        query = query.order_by(desc(CoinPoolOffer.apr)).limit(1)

        result = await session.execute(query)
        offer = result.unique().scalar_one_or_none()

        if not offer:
            raise HTTPException(status_code=404, detail="No matching offer found")

        return OfferResponse.model_validate(offer)

    except SQLAlchemyError as e:
        logger.exception(f"Database error occurred in get_max_apr_offer: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error occurred in get_max_apr_offer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
