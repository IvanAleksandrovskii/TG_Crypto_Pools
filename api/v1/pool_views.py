from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core import logger
from core.models import db_helper, Pool
from core.schemas import PoolResponse
from utils import Ordering

router = APIRouter()

pool_ordering = Ordering(Pool, ["name", "id"], default_field="name")


@router.get("/", response_model=List[PoolResponse])
async def get_all_pools(
    session: AsyncSession = Depends(db_helper.session_getter),
    order: Optional[str] = Query(None, description="Order by field"),
    order_desc: Optional[bool] = Query(None, description="Order in descending order")
):
    query = Pool.active().order_by(pool_ordering.order_by(order, order_desc))
    try:
        result = await session.execute(query)
        pools = result.scalars().all()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_pools: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [PoolResponse.model_validate(pool) for pool in pools]


@router.get("/{pool_id}", response_model=PoolResponse)
async def get_pool_by_id(
        pool_id: UUID,
        session: AsyncSession = Depends(db_helper.session_getter)
):
    query = Pool.active().where(Pool.id == pool_id)
    try:
        result = await session.execute(query)
        pool = result.scalars().one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_pool_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    return PoolResponse.model_validate(pool)
