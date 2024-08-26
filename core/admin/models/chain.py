from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import validators, SelectMultipleField
from wtforms.fields import FileField
from wtforms.widgets import ListWidget, CheckboxInput

from core.models import Chain, Coin
from core import logger, chain_storage
from .base import BaseAdminModel


class ChainAdmin(BaseAdminModel, model=Chain):
    column_list = [Chain.name, Chain.is_active, Chain.id, Chain.logo]
    column_sortable_list = [Chain.name, Chain.is_active]
    column_searchable_list = [Chain.name]
    column_filters = [Chain.is_active, Chain.name]

    form_columns = ['name', 'coins', 'is_active', 'logo']
    form_args = {
        'name': {'validators': [validators.DataRequired()]},
        'logo': {'validators': [validators.Optional()]}
    }

    form_widget_args = {
        'name': {
            'placeholder': 'Enter chain\'s name'
        },
    }

    async def search_query(self, stmt, term):
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
        form_class.logo = FileField('Logo')
        return form_class

    def _coerce_coin(self, value):
        if hasattr(value, 'id'):
            return str(value.id)
        return str(value)

    async def _get_coin_choices(self):
        async with self.session as session:
            result = await session.execute(select(Coin).where(Coin.is_active == True))
            coins = result.scalars().all()
            return [(str(coin.id), f"{coin.name} ({coin.code})") for coin in coins]

    async def get_one(self, _id):
        async with self.session as session:
            stmt = select(self.model).options(
                selectinload(Chain.coins)
            ).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def after_model_change(self, data: dict, model: Chain, is_created: bool, request: Request) -> None:
        try:
            action = "Created" if is_created else "Updated"
            logger.info(f"{action} Chain successfully with id: {model.id}")

            # Process logo upload
            logo = data.get('logo')
            if logo and isinstance(logo, UploadFile):
                try:
                    file_path = await chain_storage.put(logo)
                    model.logo = file_path
                    logger.info(f"Logo uploaded for chain: {model.name}")

                    async with self.session as session:
                        await session.merge(model)
                        await session.commit()
                except Exception as e:
                    logger.error(f"Error uploading logo for chain {model.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in after_model_change for {self.name}: {str(e)}")
            raise HTTPException(status_code=500,
                                detail=f"An unexpected error occurred while create/update {self.name}. Error: {str(e)}")

    async def delete_model(self, request: Request, pk: Any):
        model = await self.get_one(pk)
        if model and model.logo:
            try:
                chain_storage.delete(model.logo)
                logger.info(f"Logo deleted for chain: {model.name}")
            except Exception as e:
                logger.error(f"Error deleting logo for chain {model.name}: {str(e)}")
        return await super().delete_model(request, pk)
