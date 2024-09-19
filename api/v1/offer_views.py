from datetime import datetime, timedelta, UTC
from typing import List, Optional
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


# TODO: Add pagination


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
        query = await get_latest_offers()

        if coin_id:
            query = query.filter(CoinPoolOffer.coin_id == coin_id)
        if chain_id:
            query = query.filter(CoinPoolOffer.chain_id == chain_id)
        if pool_id:
            query = query.filter(CoinPoolOffer.pool_id == pool_id)

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
        historical_price_query = select(CoinPrice).filter(
            CoinPrice.coin_id == base_offer.coin_id,
            CoinPrice.created_at <= base_offer.created_at
        ).order_by(CoinPrice.created_at.desc()).limit(1)
        historical_price_result = await session.execute(historical_price_query)
        historical_price = historical_price_result.scalar_one_or_none()
        base_offer.historical_coin_price = historical_price.price if historical_price else None

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
