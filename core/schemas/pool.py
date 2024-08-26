from .base import BaseResponse


class PoolResponse(BaseResponse):
    name: str
    website_url: str
    logo: str

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            name=obj.name,
            website_url=obj.website_url,
            logo=obj.logo,
        )
