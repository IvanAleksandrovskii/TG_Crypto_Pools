from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from core import settings


class AsyncDataBaseHelper:
    def __init__(self, url: str, echo: bool):
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
        )

    async def dispose(self):
        await self.engine.dispose()


async_sqladmin_db_helper = AsyncDataBaseHelper(
    url=settings.db.url,
    echo=False,
)
