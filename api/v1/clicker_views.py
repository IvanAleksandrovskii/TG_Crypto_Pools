from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper, Clicker
from core.schemas import ClickerResponse
from utils import Ordering

router = APIRouter()


# Define the allowed fields for ordering
ALLOWED_ORDER_FIELDS = ["name", "coin", "audience", "app_launch_date", "token_launch_date"]

clicker_ordering = Ordering(Clicker, ALLOWED_ORDER_FIELDS, default_field="audience", default_desc=True)

@router.get("/", response_model=List[ClickerResponse])
async def get_all_clickers(
    session: AsyncSession = Depends(db_helper.session_getter),
    order: Optional[str] = Query(None, description="Field to order by"),
    order_desc: Optional[bool] = Query(None, description="Order descending if true")
):
    query = Clicker.active().where(Clicker.is_active == True)
    query = query.order_by(clicker_ordering.order_by(order, order_desc))

    result = await session.execute(query)
    clickers = result.scalars().all()
    return [ClickerResponse.model_validate(clicker) for clicker in clickers]


@router.get("/{clicker_id}", response_model=ClickerResponse)
async def get_clicker_by_id(clicker_id: UUID, session: AsyncSession = Depends(db_helper.session_getter)):
    query = Clicker.active().where(Clicker.id == clicker_id, Clicker.is_active == True)
    result = await session.execute(query)
    clicker = result.scalar_one_or_none()
    if not clicker:
        raise HTTPException(status_code=404, detail="Clicker not found")
    return ClickerResponse.model_validate(clicker)
