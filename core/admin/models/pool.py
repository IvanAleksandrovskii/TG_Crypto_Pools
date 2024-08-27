from typing import Any
from starlette.requests import Request
from wtforms import validators
from wtforms.fields import FileField
from fastapi import HTTPException, UploadFile

from core.models import Pool
from core import logger, pool_storage
from .base import BaseAdminModel


class PoolAdmin(BaseAdminModel, model=Pool):
    column_list = [Pool.name, Pool.is_active, Pool.website_url, Pool.id, Pool.logo]
    column_sortable_list = [Pool.name, Pool.is_active]
    column_searchable_list = [Pool.name, Pool.website_url]
    column_filters = [Pool.is_active, Pool.name]
    column_details_list = ['name', 'website_url', 'is_active', 'id', 'logo', 'coin_pool_offers']

    form_columns = ['name', 'website_url', 'is_active', 'logo']
    form_args = {
        'name': {'validators': [validators.DataRequired()]},
        'website_url': {'validators': [validators.DataRequired(), validators.URL()]},
        'logo': {'validators': [validators.Optional()]}
    }

    async def search_query(self, stmt, term):
        return stmt.filter(Pool.name.ilike(f"%{term}%"))

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.logo = FileField('Logo')
        return form_class

    async def after_model_change(self, data: dict, model: Pool, is_created: bool, request: Request):
        try:
            action = "Created" if is_created else "Updated"
            logger.info(f"{action} Pool successfully with id: {model.id}")

            # Process logo upload
            logo = data.get('logo')
            if logo and isinstance(logo, UploadFile):
                try:
                    file_path = await pool_storage.put(logo)
                    model.logo = file_path
                    logger.info(f"Logo uploaded for pool: {model.name}")

                    async with self.session as session:
                        await session.merge(model)
                        await session.commit()

                except Exception as e:
                    logger.error(f"Error uploading logo for pool {model.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in after_model_change for {self.name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while create/update {self.name}. Error: {str(e)}")

    async def delete_model(self, request: Request, pk: Any):
        model = await self.get_one(pk)
        if model and model.logo:
            try:
                pool_storage.delete(model.logo)
                logger.info(f"Logo deleted for pool: {model.name}")
            except Exception as e:
                logger.error(f"Error deleting logo for pool {model.name}: {str(e)}")
        return await super().delete_model(request, pk)
