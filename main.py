import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncio
from icecream import ic

from fastapi.responses import ORJSONResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
from sqladmin import Admin

from core.admin import async_sqladmin_db_helper, sqladmin_authentication_backend
from core.models import db_helper, check_and_update_tables
from core.admin.models import setup_admin
from core import settings, logger
from api import api_router

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services import update_coin_prices
from scraping import run_parsing_with_delay

from clickers_services import init_clickers

from core.models import check_table

from bot_main import main as start_bot


ic.disable()
# ic.enable()


def run_async(func):
    loop = asyncio.get_event_loop()
    return lambda: loop.create_task(func())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # not used: ignore
    # Startup
    logger.info("Starting up the FastAPI application...")

    await init_clickers()

    # Create or update TG Log tables
    await check_and_update_tables(engine=async_sqladmin_db_helper.engine)
    # Create or update TG Welcome Message table
    await check_table(engine=async_sqladmin_db_helper.engine)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_async(update_coin_prices),
        'cron',
        minute='*/' + str(settings.scheduler.currency_update_interval)
    )
    scheduler.add_job(
        run_async(run_parsing_with_delay),
        'cron',
        hour=str(settings.scheduler.offers_update_hour),
    )
    scheduler.start()

    # Start the bot in a separate task
    bot_task = asyncio.create_task(start_bot())

    yield

    # Shutdown
    logger.info("Shutting down the FastAPI application...")
    scheduler.shutdown()
    await db_helper.dispose()
    await async_sqladmin_db_helper.dispose()

    # Cancel the bot task
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Bot task cancelled successfully")


main_app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

# SQLAdmin
admin = Admin(main_app, engine=async_sqladmin_db_helper.engine, authentication_backend=sqladmin_authentication_backend)

# Register admin views
setup_admin(admin)

main_app.include_router(api_router, prefix=settings.api.prefix)

# Mount static file directories
main_app.mount("/media/coins", StaticFiles(directory=settings.media.coins_path), name="coins_media")
main_app.mount("/media/pools", StaticFiles(directory=settings.media.pools_path), name="pools_media")
main_app.mount("/media/chains", StaticFiles(directory=settings.media.chains_path), name="chains_media")
main_app.mount("/media/clickers", StaticFiles(directory=settings.media.clickers_path), name="clickers_media")


# Favicon.ico errors silenced
@main_app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# Global exception handler
@main_app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        if request.url.path == "/favicon.ico":
            return Response(status_code=204)

        if isinstance(exc, ValueError) and "badly formed hexadecimal UUID string" in str(exc):
            return Response(status_code=204)

        logger.error(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )


class NoFaviconFilter(logging.Filter):
    def filter(self, record):
        return not any(x in record.getMessage() for x in ['favicon.ico', 'apple-touch-icon'])


logging.getLogger("uvicorn.access").addFilter(NoFaviconFilter())

# CORS
main_app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == '__main__':
    uvicorn.run("main:main_app",
                host=ic(settings.run.host),
                port=ic(settings.run.port),
                reload=ic(settings.run.debug),
                )
