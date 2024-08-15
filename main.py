from contextlib import asynccontextmanager
from typing import AsyncGenerator
from icecream import ic

from fastapi.responses import ORJSONResponse
from fastapi import FastAPI
import uvicorn

from core.models import db_helper
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


main_app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

main_app.include_router(api_router, prefix=settings.api.prefix)

if __name__ == '__main__':
    uvicorn.run(ic("main:main_app"),
                host=ic(settings.run.host),
                port=ic(settings.run.port),
                reload=ic(settings.run.debug),
                )
