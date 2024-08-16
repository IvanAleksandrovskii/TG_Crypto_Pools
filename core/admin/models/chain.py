from starlette.requests import Request
from wtforms import validators
from sqlalchemy.orm import joinedload

from core.models import Chain
from core import logger
from .base import BaseAdminModel


class ChainAdmin(BaseAdminModel, model=Chain):
    column_list = [Chain.id, Chain.name, 'coins', Chain.is_active]
    column_formatters = {
        Chain.id: lambda m, a: str(m)
    }
    column_sortable_list = [Chain.name, Chain.is_active]
    column_searchable_list = [Chain.name]
    column_filters = [Chain.is_active, Chain.name]

    form_columns = ['name', 'coins', 'is_active']
    form_args = {
        'name': {'validators': [validators.DataRequired()]}
    }

    def get_query(self):
        return (
            super()
            .get_query()
            .options(
                joinedload(Chain.coins)
            )
        )

    def search_query(self, stmt, term):
        return stmt.filter(Chain.name.ilike(f"%{term}%"))

    async def after_model_change(self, data: dict, model: Chain, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} Chain successfully with id: {model.id}")
