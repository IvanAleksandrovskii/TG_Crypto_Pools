from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import logger
from core.models import db_helper, Coin, CoinPrice, Chain, coin_chain, CoinPoolOffer
from core.schemas import CoinResponse, CoinExtendedResponse
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


@router.get("/extended/", response_model=List[CoinExtendedResponse])
async def get_all_coins_extended(
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

        # Subquery to get latest offers
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

        # Subquery to get max APR and min amount_from from latest active offers
        offer_subquery = (
            select(
                CoinPoolOffer.coin_id,
                func.max(CoinPoolOffer.apr).label('max_apr'),
                func.min(CoinPoolOffer.amount_from).label('min_amount_from')
            )
            .join(
                latest_offers_subquery,
                (CoinPoolOffer.coin_id == latest_offers_subquery.c.coin_id) &
                (CoinPoolOffer.pool_id == latest_offers_subquery.c.pool_id) &
                (CoinPoolOffer.chain_id == latest_offers_subquery.c.chain_id) &
                (CoinPoolOffer.lock_period == latest_offers_subquery.c.lock_period) &
                (CoinPoolOffer.created_at == latest_offers_subquery.c.max_created_at)
            )
            .where(CoinPoolOffer.is_active == True)
            .group_by(CoinPoolOffer.coin_id)
            .subquery()
        )

        # Main query
        query = (
            select(
                Coin,
                CoinPrice.price.label('current_price'),
                offer_subquery.c.max_apr,
                offer_subquery.c.min_amount_from
            )
            .outerjoin(latest_price_subquery, Coin.id == latest_price_subquery.c.coin_id)
            .outerjoin(CoinPrice, and_(
                CoinPrice.coin_id == Coin.id,
                CoinPrice.created_at == latest_price_subquery.c.max_date
            ))
            .outerjoin(offer_subquery, Coin.id == offer_subquery.c.coin_id)
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

        query = query.order_by(coin_ordering.order_by(order, order_desc))

        result = await session.execute(query)
        coins_data = result.all()

        return [
            CoinExtendedResponse(
                id=coin.id,
                name=coin.name,
                code=coin.code,
                logo=coin.logo,
                current_price=current_price,
                max_apr=max_apr,
                min_amount_from=min_amount_from
            )
            for coin, current_price, max_apr, min_amount_from in coins_data
        ]

    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_coins_extended: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
