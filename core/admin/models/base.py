from typing import Any

from fastapi import UploadFile
from sqladmin import ModelView, action
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from core import logger
from core.admin import async_sqladmin_db_helper


class BaseAdminModel(ModelView):
    column_list = ['id', 'is_active']
    column_details_list = "__all__"  # TODO: found a way to correct the view?
    column_sortable_list = ['id', 'is_active']
    column_searchable_list = ['id']
    column_filters = ['is_active']
    # column_exclude_list = ['created_at']

    page_size = 50
    page_size_options = [25, 50, 100, 200, 500]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    form_excluded_columns = ['created_at']

    form_widget_args = {
        'id': {'readonly': True},
    }

    async def get_one(self, _id):
        async with self.session as session:
            stmt = select(self.model).options(selectinload('*')).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_form(self, form_class, obj: Any = None):
        return await super().get_form(form_class, obj)

    async def _handle_file_upload(self, field_name: str, file: UploadFile):
        if isinstance(file, UploadFile):
            content = await file.read()
        else:
            raise ValueError(f"Unsupported file type for {field_name}")
        return content

    async def _update_model_fields(self, session: AsyncSession, model: Any, data: dict):
        for key, value in data.items():
            if hasattr(model, key):
                setattr(model, key, value)

    async def _process_action(self, request: Request, is_active: bool) -> None:
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            async with self.session as session:
                async with session.begin():
                    for pk in pks:
                        model = await session.get(self.model, pk)
                        if model:
                            model.is_active = is_active
                    await session.commit()
                logger.info(f"Successfully {'activated' if is_active else 'deactivated'} {len(pks)} {self.name}(s)")

    @action(
        name="activate",
        label="Activate",
        confirmation_message="Are you sure you want to activate selected %(model)s?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def activate(self, request: Request) -> RedirectResponse:
        await self._process_action(request, True)
        return RedirectResponse(request.url_for("admin:list", identity=self.identity), status_code=302)

    @action(
        name="deactivate",
        label="Deactivate",
        confirmation_message="Are you sure you want to deactivate selected %(model)s?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def deactivate(self, request: Request) -> RedirectResponse:
        await self._process_action(request, False)
        return RedirectResponse(request.url_for("admin:list", identity=self.identity), status_code=302)

    @property
    def session(self):
        return AsyncSession(async_sqladmin_db_helper.engine)
