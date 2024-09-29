from typing import Optional

from pydantic import BaseModel
from datetime import date
from uuid import UUID


class ClickerResponse(BaseModel):
    id: UUID
    name: Optional[str]
    description: Optional[str]
    time_spent: Optional[str]
    link: Optional[str]
    audience: Optional[str]
    coin: Optional[str]
    app_launch_date: Optional[date]
    token_launch_date: Optional[date]
    telegram_channel: Optional[str]
    partners: Optional[str]
    comment: Optional[str]

    class Config:
        from_attributes = True
