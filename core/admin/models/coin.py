from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload
from starlette.requests import Request
from wtforms import validators, SelectMultipleField
from wtforms.widgets import ListWidget, CheckboxInput

from core.models import Coin, Chain
from core import logger
from .base import BaseAdminModel


class CoinAdmin(BaseAdminModel, model=Coin):
    column_list = [Coin.code, Coin.is_active, Coin.name, Coin.id, ]  # , 'chains', 'pools'
    column_sortable_list = [Coin.name, Coin.code, Coin.is_active]
    column_searchable_list = [Coin.name, Coin.code]
    column_filters = [Coin.is_active, Coin.name, Coin.code]

    can_delete = False

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

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.chains = SelectMultipleField(
            'Chains',
            choices=await self._get_chain_choices(),
            widget=ListWidget(prefix_label=False),
            option_widget=CheckboxInput(),
            coerce=self._coerce_chain
        )
        return form_class

    def _coerce_chain(self, value):
        if hasattr(value, 'id'):
            return str(value.id)
        return str(value)

    async def _get_chain_choices(self):
        async with self.session_getter() as session:
            result = await session.execute(select(Chain).where(Chain.is_active == True))
            chains = result.scalars().all()
            return [(str(chain.id), chain.name) for chain in chains]

    async def get_one(self, _id):
        async with self.session_getter() as session:
            stmt = select(self.model).options(
                joinedload(Coin.chains)
            ).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def edit_form(self, obj):
        form = await super().edit_form(obj)
        if obj and obj.chains:
            form.chains.data = [str(chain.id) for chain in obj.chains]
        return form

    async def _update_model_fields(self, session, model, data):
        await super()._update_model_fields(session, model, data)
        if 'chains' in data:
            chain_ids = data['chains']
            stmt = select(Chain).where(Chain.id.in_(chain_ids))
            result = await session.execute(stmt)
            chains = result.scalars().all()
            model.chains = chains

    async def after_model_change(self, data: dict, model: Coin, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} Coin successfully with id: {model.id}")
