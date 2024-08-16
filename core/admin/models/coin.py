from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from starlette.requests import Request
from wtforms import validators

from core.models import Coin
from core import logger
from .base import BaseAdminModel


# TODO: add coin symbol field (?)
class CoinAdmin(BaseAdminModel, model=Coin):
    column_list = [Coin.id, Coin.name, Coin.code, 'chains', 'pools', Coin.is_active]
    column_formatters = {
        Coin.id: lambda m, a: str(m)
    }
    column_sortable_list = [Coin.name, Coin.code, Coin.is_active]
    column_searchable_list = [Coin.name, Coin.code]
    column_filters = [Coin.is_active, Coin.name, Coin.code]

    form_columns = ['name', 'code', 'chains', 'is_active']
    form_args = {
        'name': {'validators': [validators.DataRequired()]},
        'code': {'validators': [validators.DataRequired()]}
    }

    def get_query(self):
        return (
            super()
            .get_query()
            .options(
                joinedload(Coin.chains),
                joinedload(Coin.pools)
            )
        )

    def search_query(self, stmt, term):
        return stmt.filter(or_(Coin.name.ilike(f"%{term}%"), Coin.code.ilike(f"%{term}%")))

    async def after_model_change(self, data: dict, model: Coin, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} Coin successfully with id: {model.id}")
