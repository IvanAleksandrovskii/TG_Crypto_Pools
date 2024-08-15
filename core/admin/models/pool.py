from starlette.requests import Request
from wtforms import validators
from sqlalchemy.orm import joinedload

from core.models import Pool
from core import logger
from .base import BaseAdminModel


class PoolAdmin(BaseAdminModel, model=Pool):
    column_list = [Pool.id, Pool.name, Pool.website_url, 'coin_pool_offers', Pool.is_active]
    column_sortable_list = [Pool.name, Pool.is_active]
    column_searchable_list = [Pool.name, Pool.website_url]
    column_filters = [Pool.is_active, Pool.name]

    form_columns = ['name', 'website_url', 'is_active']
    form_args = {
        'name': {'validators': [validators.DataRequired()]},
        'website_url': {'validators': [validators.DataRequired(), validators.URL()]}
    }

    def get_query(self):
        return (
            super()
            .get_query()
            .options(
                joinedload(Pool.coin_pool_offers)
            )
        )

    def search_query(self, stmt, term):
        return stmt.filter(Pool.name.ilike(f"%{term}%"))

    async def after_model_change(self, data: dict, model: Pool, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} Pool successfully with id: {model.id}")
