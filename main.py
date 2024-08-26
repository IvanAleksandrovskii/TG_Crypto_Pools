import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from icecream import ic

from fastapi.responses import ORJSONResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Response, Request
import uvicorn
from sqladmin import Admin

from core.admin import async_sqladmin_db_helper, sqladmin_authentication_backend
from core.models import db_helper
from core.admin.models import setup_admin
from core import settings, logger
from api import api_router

ic.disable()
# ic.enable()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("Starting up the FastAPI application...")

    yield

    # Shutdown
    logger.info("Shutting down the FastAPI application...")
    await db_helper.dispose()
    await async_sqladmin_db_helper.dispose()


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

if __name__ == '__main__':
    uvicorn.run(ic("main:main_app"),
                host=ic(settings.run.host),
                port=ic(settings.run.port),
                reload=ic(settings.run.debug),
                )
