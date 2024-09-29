from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload  # unused: ignore, error in IDE, it is used!

from core import logger
from core.models import db_helper, CoinPoolOffer, Coin, Pool, Chain, CoinPrice
from core.schemas import (
    OfferResponse, OfferResponseWithHistory, OfferHistory,
    PoolResponse, ChainResponse, CoinResponse, PaginatedOfferResponse, PaginationMetadata,
)
from utils import Ordering

router = APIRouter()

offer_ordering = Ordering(CoinPoolOffer,
                          [
                              "lock_period", "apr", "created_at", "amount_from",
                              "pool_share", "liquidity_token", "liquidity_token_name",
                              "coin_id", "pool_id", "chain_id", "id",
                          ],
                          default_field="apr",
                          default_desc=True,
                          )


async def get_latest_offers():
    subquery = (
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
            joinedload(CoinPoolOffer.coin).selectinload(Coin.prices),
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


@router.get("/", response_model=PaginatedOfferResponse)
async def get_all_offers(
        coin_id: Optional[UUID] = Query(None, description="Filter by coin ID"),
        chain_id: Optional[UUID] = Query(None, description="Filter by chain ID"),
        pool_id: Optional[UUID] = Query(None, description="Filter by pool ID"),
        apr_from: Optional[float] = Query(None, ge=0, description="Minimum APR"),
        apr_to: Optional[float] = Query(None, ge=0, description="Maximum APR"),
        lock_period_from: Optional[int] = Query(None, ge=0, description="Minimum lock period"),
        lock_period_to: Optional[int] = Query(None, description="Maximum lock period"),
        amount_from: Optional[float] = Query(None, ge=0, description="Minimum amount"),
        amount_to: Optional[float] = Query(None, description="Maximum amount"),
        pool_share_from: Optional[float] = Query(None, ge=0, description="Minimum pool share"),
        pool_share_to: Optional[float] = Query(None, description="Maximum pool share"),
        session: AsyncSession = Depends(db_helper.session_getter),
        order: Optional[str] = Query(None, description="Order by field"),
        order_desc: Optional[bool] = Query(None, description="Order in descending order"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    try:
        query = await get_latest_offers()

        if coin_id:
            query = query.filter(CoinPoolOffer.coin_id == coin_id)
        if chain_id:
            query = query.filter(CoinPoolOffer.chain_id == chain_id)
        if pool_id:
            query = query.filter(CoinPoolOffer.pool_id == pool_id)

        # APR filter
        if apr_from is not None:
            query = query.filter(CoinPoolOffer.apr >= apr_from)
        if apr_to is not None:
            query = query.filter(CoinPoolOffer.apr <= apr_to)

        # Lock period filter
        if lock_period_from is not None:
            query = query.filter(CoinPoolOffer.lock_period >= lock_period_from)
        if lock_period_to is not None:
            query = query.filter(CoinPoolOffer.lock_period <= lock_period_to)

        # Amount filter
        if amount_from is not None:
            query = query.filter(CoinPoolOffer.amount_from >= amount_from)
        if amount_to is not None:
            query = query.filter(CoinPoolOffer.amount_from <= amount_to)

        # Pool share filter
        if pool_share_from is not None:
            query = query.filter(CoinPoolOffer.pool_share >= pool_share_from)
        if pool_share_to is not None:
            query = query.filter(CoinPoolOffer.pool_share <= pool_share_to)

        # Apply ordering
        query = query.order_by(offer_ordering.order_by(order, order_desc))

        # Count total items
        count_query = query.with_only_columns(func.count().label("count")).order_by(None)
        total_items = await session.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        offers = result.unique().scalars().all()

        total_pages = (total_items + page_size - 1) // page_size

        logger.info(f"Number of offers retrieved: {len(offers)}")

        return PaginatedOfferResponse(
            items=[OfferResponse.model_validate(offer) for offer in offers],
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                total_items=total_items
            )
        )

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
        base_query = (
            CoinPoolOffer.active()
            .options(
                joinedload(CoinPoolOffer.coin).selectinload(Coin.prices),
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

        # Get historical price for base offer
        # historical_price_query = select(CoinPrice).filter(
        #     CoinPrice.coin_id == base_offer.coin_id,
        #     CoinPrice.created_at <= base_offer.created_at
        # ).order_by(CoinPrice.created_at.desc()).limit(1)
        # historical_price_result = await session.execute(historical_price_query)
        # historical_price = historical_price_result.scalar_one_or_none()
        # base_offer.historical_coin_price = historical_price.price if historical_price else None

        if days is None:
            history = [OfferHistory.model_validate(base_offer)]
        else:
            start_date = datetime.now(UTC) - timedelta(days=days)

            history_query = (
                select(CoinPoolOffer)
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
            offers = result.scalars().all()

            history = []
            for offer in offers:
                historical_price_query = select(CoinPrice).filter(
                    CoinPrice.coin_id == offer.coin_id,
                    CoinPrice.created_at <= offer.created_at
                ).order_by(CoinPrice.created_at.desc()).limit(1)
                historical_price_result = await session.execute(historical_price_query)
                historical_price = historical_price_result.scalar_one_or_none()
                offer.historical_coin_price = historical_price.price if historical_price else None
                history.append(OfferHistory.model_validate(offer))

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
