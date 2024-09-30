from aiogram import Bot, Dispatcher

from core import settings
from bot.bot_logger import logger
from bot.handlers import router as tg_router


BOT_TOKEN = settings.bot.token

dp = Dispatcher()
dp.include_router(tg_router)


async def main():
    bot = Bot(token=BOT_TOKEN)

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.exception(f"Error starting bot: {e}")

    finally:
        logger.info("Disposing bot...")
        await bot.session.close()
