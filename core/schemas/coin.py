from typing import Optional

from pydantic import Field

from .base import BaseResponse


class CoinResponse(BaseResponse):
    name: Optional[str]
    code: str
    logo: Optional[str] = Field(None, )
    current_price: Optional[float] = Field(None, description="Current price of the coin")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        logo_path = obj.logo
        if logo_path and logo_path.startswith("/app/"):
            logo_path = logo_path[4:]  # Remove "/app" prefix
        return cls(
            id=obj.id,
            name=obj.name,
            code=obj.code,
            logo=logo_path,
            current_price=obj.latest_price.price if obj.latest_price else None,
        )


class CoinExtendedResponse(CoinResponse):
    max_apr: Optional[float] = Field(None, description="Maximum APR from active offers")
    min_amount_from: Optional[float] = Field(None, description="Minimum amount_from from active offers")

    class Config:
        from_attributes = True
