from typing import Optional

from pydantic import Field

from .base import BaseResponse


class CoinResponse(BaseResponse):
    name: str
    code: str
    logo: Optional[str] = Field(None, )

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            name=obj.name,
            code=obj.code,
            logo=obj.logo
        )
