from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core import logger
from core.models import db_helper, Chain
from core.schemas import ChainResponse
from utils import Ordering

router = APIRouter()

chain_ordering = Ordering(Chain, ["name", "id"], default_field="name")


@router.get("/", response_model=List[ChainResponse])
async def get_all_chains(
    session: AsyncSession = Depends(db_helper.session_getter),
    order: Optional[str] = Query(None, description="Order by field"),
    order_desc: Optional[bool] = Query(None, description="Order in descending order")
):
    query = Chain.active().order_by(chain_ordering.order_by(order, order_desc))
    try:
        result = await session.execute(query)
        chains = result.scalars().all()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_all_chains: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [ChainResponse.model_validate(chain) for chain in chains]


@router.get("/{chain_id}", response_model=ChainResponse)
async def get_chain_by_id(
        chain_id: UUID,
        session: AsyncSession = Depends(db_helper.session_getter)
):
    query = Chain.active().where(Chain.id == chain_id)
    try:
        result = await session.execute(query)
        chain = result.scalars().one_or_none()
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected error occurred in get_chain_by_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    return ChainResponse.model_validate(chain)
