from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import validators, SelectMultipleField
from wtforms.fields import FileField
from wtforms.widgets import ListWidget, CheckboxInput

from core.models import Coin, Chain
from core import logger, coin_storage
from .base import BaseAdminModel


class CoinAdmin(BaseAdminModel, model=Coin):
    column_list = [Coin.code, Coin.is_active, Coin.name, Coin.id, Coin.logo]
    column_sortable_list = [Coin.name, Coin.code, Coin.is_active]
    column_searchable_list = [Coin.name, Coin.code]
    column_filters = [Coin.is_active, Coin.name, Coin.code]
    column_details_list = ['name', 'code', 'is_active', 'id', 'logo', 'chains', 'pools']

    form_columns = ['name', 'code', 'chains', 'is_active', 'logo']
    form_args = {
        'name': {'validators': [validators.DataRequired()]},
        'code': {'validators': [validators.DataRequired()]},
        'logo': {'validators': [validators.Optional()]}
    }

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.chains = SelectMultipleField(
            'Chains',
            choices=await self._get_chain_choices(),
            widget=ListWidget(prefix_label=False),
            option_widget=CheckboxInput(),
            coerce=self._coerce_chain
        )
        form_class.logo = FileField('Logo')
        return form_class

    def _coerce_chain(self, value):
        if hasattr(value, 'id'):
            return str(value.id)
        return str(value)

    async def _get_chain_choices(self):
        async with self.session as session:
            result = await session.execute(select(Chain).where(Chain.is_active == True))
            chains = result.scalars().all()
            return [(str(chain.id), chain.name) for chain in chains]

    async def get_one(self, _id):
        async with self.session as session:
            stmt = select(self.model).options(
                selectinload(Coin.chains)
            ).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def after_model_change(self, data: dict, model: Coin, is_created: bool, request: Request) -> None:
        try:
            action = "Created" if is_created else "Updated"
            logger.info(f"{action} Coin successfully with id: {model.id}")

            # Process logo upload
            logo = data.get('logo')
            if logo and isinstance(logo, UploadFile):
                try:
                    file_path = await coin_storage.put(logo)
                    model.logo = file_path
                    logger.info(f"Logo uploaded for coin: {model.name}")

                    async with self.session as session:
                        await session.merge(model)
                        await session.commit()
                except Exception as e:
                    logger.error(f"Error uploading logo for coin {model.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in after_model_change for {self.name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while create/update {self.name}. Error: {str(e)}")

    async def delete_model(self, request: Request, pk: Any):
        model = await self.get_one(pk)
        if model and model.logo:
            try:
                coin_storage.delete(model.logo)
                logger.info(f"Logo deleted for coin: {model.name}")
            except Exception as e:
                logger.error(f"Error deleting logo for coin {model.name}: {str(e)}")
        return await super().delete_model(request, pk)
