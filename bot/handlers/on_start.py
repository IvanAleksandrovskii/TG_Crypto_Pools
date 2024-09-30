from aiogram import types, Router
from aiogram.filters import CommandStart

from bot import UserService, logger
from core import settings
from core.models import db_helper, WelcomeMessage


router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message):
    username = message.from_user.username
    chat_id = int(message.chat.id)

    user_service = UserService()

    async for session in db_helper.session_getter():
        try:
            # Get welcome message
            welcome_message = await WelcomeMessage.get_message(session)

            user = await user_service.get_user(chat_id)
            if not user:
                user = await user_service.create_user(chat_id, username)
                logger.info("Created new user: %s, username: %s", user.tg_user, user.username)

            elif user.username != username:
                updated = await user_service.update_username(chat_id, username)
                if updated:
                    logger.info("Updated username for user %s to %s", chat_id, username)
                else:
                    logger.warning("Failed to update username for user %s", chat_id)

                logger.info("Updated username for user %s to %s", user.tg_user, user.username)

            if welcome_message and '{username}' in welcome_message:
                formatted_message = welcome_message.format(username=username or "пользователь")
            else:
                formatted_message = welcome_message

            await message.answer(formatted_message)

        except Exception as e:
            logger.error(f"Database error in start_handler: {e}")

            await message.answer(settings.bot.user_error_message)

        finally:
            await session.close()
