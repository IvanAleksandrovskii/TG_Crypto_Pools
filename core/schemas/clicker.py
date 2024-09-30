from typing import Optional
from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID


class ClickerResponse(BaseModel):
    id: UUID
    name: Optional[str]
    description: Optional[str]
    time_spent: Optional[str]
    link: Optional[str]
    audience: Optional[int]
    coin: Optional[str]
    app_launch_date: Optional[date]
    token_launch_date: Optional[date]
    telegram_channel: Optional[str]
    partners: Optional[str]
    comment: Optional[str]
    logo: Optional[str] = Field(None, description="Path to the logo image")

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        logo_path = obj.logo
        if logo_path and logo_path.startswith("/app/"):
            logo_path = logo_path[4:]  # Remove "/app" prefix
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description,
            time_spent=obj.time_spent,
            link=obj.link,
            audience=obj.audience,
            coin=obj.coin,
            app_launch_date=obj.app_launch_date,
            token_launch_date=obj.token_launch_date,
            telegram_channel=obj.telegram_channel,
            partners=obj.partners,
            comment=obj.comment,
            logo=logo_path,
        )
