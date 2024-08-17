from sqlalchemy import select
from sqlalchemy.orm import joinedload
from starlette.requests import Request
from wtforms import validators, SelectMultipleField
from wtforms.widgets import ListWidget, CheckboxInput

from core.models import Chain, Coin
from core import logger
from .base import BaseAdminModel


class ChainAdmin(BaseAdminModel, model=Chain):
    column_list = [Chain.name, Chain.is_active, Chain.id, ]  # , 'coins'
    column_sortable_list = [Chain.name, Chain.is_active]
    column_searchable_list = [Chain.name]
    column_filters = [Chain.is_active, Chain.name]

    can_delete = False

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

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.coins = SelectMultipleField(
            'Coins',
            choices=await self._get_coin_choices(),
            widget=ListWidget(prefix_label=False),
            option_widget=CheckboxInput(),
            coerce=self._coerce_coin
        )
        return form_class

    def _coerce_coin(self, value):
        if hasattr(value, 'id'):
            return str(value.id)
        return str(value)

    async def _get_coin_choices(self):
        async with self.session_getter() as session:
            result = await session.execute(select(Coin).where(Coin.is_active == True))
            coins = result.scalars().all()
            return [(str(coin.id), f"{coin.name} ({coin.code})") for coin in coins]

    async def get_one(self, _id):
        async with self.session_getter() as session:
            stmt = select(self.model).options(
                joinedload(Chain.coins)
            ).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def edit_form(self, obj):
        form = await super().edit_form(obj)
        if obj and obj.coins:
            form.coins.data = [str(coin.id) for coin in obj.coins]
        return form

    async def _update_model_fields(self, session, model, data):
        await super()._update_model_fields(session, model, data)
        if 'coins' in data:
            coin_ids = data['coins']
            coins = await session.execute(select(Coin).where(Coin.id.in_(coin_ids)))
            model.coins = coins.scalars().all()

    async def after_model_change(self, data: dict, model: Chain, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} Chain successfully with id: {model.id}")
