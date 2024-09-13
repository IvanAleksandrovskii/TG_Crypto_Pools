from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core import logger
from core.models import db_helper, CoinPoolOffer, Coin, Pool, Chain
from core.schemas import (
    OfferResponse, OfferResponseWithHistory, OfferHistory,
    PoolResponse, ChainResponse, CoinResponse,
)
from utils import Ordering

router = APIRouter()

offer_ordering = Ordering(CoinPoolOffer,
                          [
                              "lock_period", "apr", "created_at", "amount_from",
                              "pool_share", "liquidity_token", "liquidity_token_name",
                              "coin_id", "pool_id", "chain_id", "id",
                          ],
                          default_field="pool_id")


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

        logger.info(f"Number of offers retrieved: {len(offers)}")
        for offer in offers:
            logger.info(f"Offer ID: {offer.id}, Coin: {offer.coin.code}, Pool: {offer.pool.name}")

        return [OfferResponse.model_validate(offer) for offer in offers]

    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_offers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{offer_id}", response_model=OfferResponseWithHistory)
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
            .where(Pool.is_active == True)
            .where(Coin.is_active == True)
            .where(Chain.is_active == True)
            .filter(CoinPoolOffer.id == offer_id)
        )
        result = await session.execute(base_query)
        base_offer = result.unique().scalar_one_or_none()

        if not base_offer:
            raise HTTPException(status_code=404, detail="Offer not found")

        if days is None:
            # If days is not provided, return only the current offer in history
            history = [OfferHistory.model_validate(base_offer)]
        else:
            # If days is provided, get the offer history
            start_date = datetime.now(UTC) - timedelta(days=days)

            history_query = (
                select(CoinPoolOffer)
                .options(
                    joinedload(CoinPoolOffer.coin),
                    joinedload(CoinPoolOffer.pool),
                    joinedload(CoinPoolOffer.chain)
                )
                .filter(
                    CoinPoolOffer.coin_id == base_offer.coin_id,
                    CoinPoolOffer.pool_id == base_offer.pool_id,
                    CoinPoolOffer.chain_id == base_offer.chain_id,
                    CoinPoolOffer.lock_period == base_offer.lock_period,
                    CoinPoolOffer.created_at >= start_date,
                    CoinPoolOffer.is_active == True,
                )
                .order_by(CoinPoolOffer.created_at.desc())
            )
            result = await session.execute(history_query)
            offers = result.unique().scalars().all()

            history = [OfferHistory.model_validate(offer) for offer in offers]

        return OfferResponseWithHistory(
            id=base_offer.id,
            pool=PoolResponse.model_validate(base_offer.pool),
            chain=ChainResponse.model_validate(base_offer.chain),
            coin=CoinResponse.model_validate(base_offer.coin),
            lock_period=base_offer.lock_period,
            liquidity_token=base_offer.liquidity_token,
            liquidity_token_name=base_offer.liquidity_token_name,
            history=history
        )

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

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception(f"Database error occurred in get_max_apr_offer: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error occurred in get_max_apr_offer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/debug/active-records", response_model=Dict[str, int])
async def get_active_records_count(session: AsyncSession = Depends(db_helper.session_getter)):
    try:
        coin_pool_offers_count = await session.execute(
            select(func.count()).select_from(CoinPoolOffer).where(CoinPoolOffer.is_active == True))
        coins_count = await session.execute(select(func.count()).select_from(Coin).where(Coin.is_active == True))
        pools_count = await session.execute(select(func.count()).select_from(Pool).where(Pool.is_active == True))
        chains_count = await session.execute(select(func.count()).select_from(Chain).where(Chain.is_active == True))

        return {
            "active_coin_pool_offers": coin_pool_offers_count.scalar(),
            "active_coins": coins_count.scalar(),
            "active_pools": pools_count.scalar(),
            "active_chains": chains_count.scalar(),
        }
    except SQLAlchemyError as e:
        logger.exception(f"Error in get_active_records_count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
