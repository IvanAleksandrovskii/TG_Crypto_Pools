from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import db_helper, Clicker
from core.schemas import ClickerResponse


router = APIRouter()


@router.get("/", response_model=List[ClickerResponse])
async def get_all_clickers(session: AsyncSession = Depends(db_helper.session_getter)):
    query = Clicker.active().where(Clicker.is_active == True)
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
