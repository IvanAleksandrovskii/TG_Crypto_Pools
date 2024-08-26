from typing import Optional

from pydantic import Field

from .base import BaseResponse


class ChainResponse(BaseResponse):
    name: str
    logo: Optional[str] = Field(None, )

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            name=obj.name,
            logo=obj.logo,
        )
