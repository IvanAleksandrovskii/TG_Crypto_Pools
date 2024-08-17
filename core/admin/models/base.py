from typing import Any

from fastapi import HTTPException
from sqladmin import ModelView, action
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, RelationshipProperty
from starlette.requests import Request
from starlette.responses import RedirectResponse

from core import logger
from core.admin import async_sqladmin_db_helper


class BaseAdminModel(ModelView):
    column_list = ['id', 'is_active']
    column_details_list = "__all__"
    column_sortable_list = ['id', 'is_active']
    column_searchable_list = ['id']
    column_filters = ['is_active']
    column_exclude_list = ['created_at', 'updated_at']  # TODO: Unused because of create and update time fields are not implemented yet

    page_size = 50
    page_size_options = [25, 50, 100, 200, 500]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    form_excluded_columns = ['created_at', 'updated_at']
    form_widget_args = {
        'id': {'readonly': True},
    }

    def get_query(self):
        return (
            super()
            .get_query()
            .options(
                joinedload('*')
            )
        )

    def search_query(self, stmt, term):
        or_filters = []
        for column in self.column_searchable_list:
            if isinstance(column, str) and '.' in column:
                relation, field = column.split('.')
                or_filters.append(getattr(getattr(self.model, relation), field).ilike(f"%{term}%"))
            else:
                or_filters.append(getattr(self.model, column).ilike(f"%{term}%"))
        return stmt.filter(or_(*or_filters))

    async def get_one(self, _id):
        async with AsyncSession(async_sqladmin_db_helper.engine) as session:
            stmt = select(self.model).options(selectinload('*')).filter_by(id=_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def _update_model_fields(self, session: AsyncSession, model: Any, data: dict):
        for key, value in data.items():
            prop = getattr(self.model, key).property
            if isinstance(prop, RelationshipProperty):
                if prop.uselist:
                    related_model = prop.mapper.class_
                    stmt = select(related_model).where(related_model.id.in_(value))
                    result = await session.execute(stmt)
                    related_objects = result.scalars().all()
                    setattr(model, key, related_objects)
                else:
                    related_model = prop.mapper.class_
                    related_obj = await session.get(related_model, value)
                    setattr(model, key, related_obj)
            elif key.endswith('_id'):
                setattr(model, key, str(value))
            else:
                setattr(model, key, value)

    async def insert_model(self, request: Request, data: dict) -> Any:
        logger.info(f"Inserting new {self.name}")
        async with AsyncSession(async_sqladmin_db_helper.engine) as session:
            try:
                model = self.model()
                await self._update_model_fields(session, model, data)
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created {self.name} successfully with id: {model.id}")
                return model
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError in insert_model: {str(e)}")
                raise HTTPException(status_code=400, detail=f"A {self.name} with these parameters already exists.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in insert_model: {str(e)}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred while creating {self.name}.")

    async def update_model(self, request: Request, pk: Any, data: dict) -> Any:
        logger.info(f"Updating {self.name} with id: {pk}")
        async with AsyncSession(async_sqladmin_db_helper.engine) as session:
            try:
                model = await session.get(self.model, pk)
                if not model:
                    raise HTTPException(status_code=404, detail=f"{self.name} with id {pk} not found")
                await self._update_model_fields(session, model, data)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Updated {self.name} successfully with id: {model.id}")
                return model
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError in update_model: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Update violates unique constraints for {self.name}.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in update_model: {str(e)}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred while updating {self.name}.")

    async def _update_model_fields(self, session: AsyncSession, model: Any, data: dict):
        for key, value in data.items():
            prop = getattr(self.model, key).property
            if isinstance(prop, RelationshipProperty):
                related_objects = []
                for obj_id in value:
                    related_model = prop.mapper.class_
                    related_obj = await session.get(related_model, obj_id)
                    if related_obj:
                        related_objects.append(related_obj)
                setattr(model, key, related_objects)
            elif key.endswith('_id'):
                setattr(model, key, str(value))
            else:
                setattr(model, key, value)

    async def _process_action(self, request: Request, is_active: bool) -> None:
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            async with AsyncSession(async_sqladmin_db_helper.engine) as session:
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
    def session_getter(self):
        return async_sqladmin_db_helper.session_getter
