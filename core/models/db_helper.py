from icecream import ic

from sqlalchemy.ext.asyncio import (create_async_engine, AsyncEngine,
                                    async_sessionmaker, AsyncSession)
from core import settings


ic.disable()
# ic.enable()


class DataBaseHelper:
    def __init__(self, url: str, echo: bool, pool_size: int, max_overflow: int):
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def session_getter(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session


ic("db_helper")
db_helper = DataBaseHelper(
    url=ic(settings.db.url),
    echo=ic(settings.db.echo),
    pool_size=ic(settings.db.pool_size),
    max_overflow=ic(settings.db.max_overflow),
)
