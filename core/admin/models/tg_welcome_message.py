from typing import Any

from sqladmin import ModelView
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from core import logger
from core.models import WelcomeMessage, db_helper


class WelcomeMessageAdmin(ModelView, model=WelcomeMessage):
    column_list = [WelcomeMessage.text]
    form_columns = [WelcomeMessage.text]
    can_delete = False
    can_create = True
    can_edit = True
    name = "Welcome Message"
    name_plural = "Welcome Message"
    category = "Telegram"

    async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        async for session in db_helper.session_getter():
            try:
                if is_created:
                    # Check if any welcome message exists
                    existing = await session.execute(WelcomeMessage.__table__.select())
                    if existing.first():
                        raise ValueError("A Welcome Message already exists. You can only edit the existing one.")

                    # Set the text from the form data, if no data is provided, set the default text
                    model.text = data.get('text', "Welcome to our service!")
                    session.add(model)
                else:
                    # For updates, fetch the existing model from the database
                    db_model = await session.get(WelcomeMessage, model.id)
                    if db_model is None:
                        raise ValueError("Welcome Message not found in the database.")

                    # Update the text
                    db_model.text = data.get('text', db_model.text)

                await session.commit()

            except IntegrityError:
                await session.rollback()
                raise ValueError("Error saving Welcome Message. It might already exist.")

            except Exception as e:
                await session.rollback()
                logger.error(f"Error in on_model_change for WelcomeMessage: {e}")
                raise

            finally:
                await session.close()

    async def delete_model(self, request: Request, pk: Any) -> None:
        raise ValueError("Deleting Welcome Message is not allowed.")
