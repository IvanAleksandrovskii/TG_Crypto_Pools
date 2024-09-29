from fastapi import HTTPException, UploadFile
from starlette.requests import Request
from wtforms import validators
from wtforms.fields import FileField

from core.admin.models.base import BaseAdminModel
from core.models import Clicker
from core import logger, clicker_storage


class ClickerAdmin(BaseAdminModel, model=Clicker):
    column_list = ["name", "coin", "audience", "app_launch_date", "token_launch_date", "is_active", "logo"]
    column_searchable_list = ["name", "coin", "audience"]
    column_sortable_list = ["name", "coin", "audience", "app_launch_date", "token_launch_date"]
    column_filters = ["coin", "app_launch_date", "token_launch_date", "is_active"]

    form_columns = [
        "name", "description", "time_spent", "link", "audience", "coin",
        "app_launch_date", "token_launch_date", "telegram_channel", "partners", "comment", "is_active", "logo"
    ]

    column_details_list = [
        "id", "name", "description", "time_spent", "link", "audience", "coin",
        "app_launch_date", "token_launch_date", "telegram_channel", "partners", "comment", "is_active", "logo"
    ]

    form_args = {
        'logo': {'validators': [validators.Optional()]}
    }

    can_edit = True
    can_create = True
    can_delete = True

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.logo = FileField('Logo')
        return form_class

    async def after_model_change(self, data: dict, model: Clicker, is_created: bool, request: Request) -> None:
        try:
            action = "Created" if is_created else "Updated"
            logger.info(f"{action} Clicker successfully with id: {model.id}")

            # Process logo upload
            logo = data.get('logo')
            if logo and isinstance(logo, UploadFile):
                try:
                    file_path = await clicker_storage.put(logo)
                    model.logo = file_path
                    logger.info(f"Logo uploaded for clicker: {model.name}")

                    async with self.session as session:
                        await session.merge(model)
                        await session.commit()
                except Exception as e:
                    logger.error(f"Error uploading logo for clicker {model.name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in after_model_change for {self.name}: {str(e)}")
            raise HTTPException(status_code=500,
                                detail=f"An unexpected error occurred while create/update {self.name}. Error: {str(e)}")

    async def delete_model(self, request: Request, pk: str):
        model = await self.get_one(pk)
        if model and model.logo:
            try:
                clicker_storage.delete(model.logo)
                logger.info(f"Logo deleted for clicker: {model.name}")
            except Exception as e:
                logger.error(f"Error deleting logo for clicker {model.name}: {str(e)}")
        return await super().delete_model(request, pk)
