from typing import Optional

from pydantic import Field

from .base import BaseResponse


class CoinResponse(BaseResponse):
    name: Optional[str]
    code: str
    logo: Optional[str] = Field(None, )

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
        )
