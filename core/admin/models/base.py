from typing import Any

from sqladmin import ModelView, action
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse

from core import logger
from core.admin import async_sqladmin_db_helper


class BaseAdminModel(ModelView):
    column_list = ['is_active', 'id']
    column_sortable_list = ['is_active']
    column_filters = ['is_active']
    page_size = 50
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def get_form(self, form_class, obj: Any = None):
        return await super().get_form(form_class, obj)

    async def _process_action(self, request: Request, is_active: bool) -> None:
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            try:
                async with AsyncSession(async_sqladmin_db_helper.engine) as session:
                    for pk in pks:
                        model = await session.get(self.model, pk)
                        if model:
                            model.is_active = is_active
                    await session.commit()
                logger.info(f"Successfully {'activated' if is_active else 'deactivated'} {len(pks)} objects")
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                await session.rollback()

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
