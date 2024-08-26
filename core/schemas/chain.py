from .base import BaseResponse


class ChainResponse(BaseResponse):
    name: str
    logo: str

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            name=obj.name,
            logo=obj.logo,
        )
