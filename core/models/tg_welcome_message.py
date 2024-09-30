from async_lru import alru_cache
from sqlalchemy import Table, Column, String, MetaData, inspect, Integer, select
from sqlalchemy.ext.declarative import declarative_base

from core import settings
from bot.bot_logger import logger

metadata_welcome_message = MetaData()

welcome_message = Table(
    'welcome_message',
    metadata_welcome_message,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('text', String, nullable=False),
)

Base_3 = declarative_base(metadata=metadata_welcome_message)


class WelcomeMessage(Base_3):
    __table__ = welcome_message

    id = __table__.c.id
    text = __table__.c.text

    def __repr__(self):
        return f"WelcomeMessage(id={self.id}, text='{self.text}')"

    def __str__(self):
        return self.text

    @classmethod
    @alru_cache(maxsize=1, ttl=settings.bot.welcome_message_cached_time)
    async def get_message(cls, session):
        default_message = settings.bot.fallback_greeting_user_message
        try:
            result = await session.execute(select(cls))
            _welcome_message = result.scalar_one_or_none()
            return _welcome_message.text if _welcome_message else default_message

        except Exception as e:
            logger.error(f"Error in get_message: {e}")
            return default_message


async def check_table(engine):
    async with engine.begin() as conn:
        inspector = await conn.run_sync(inspect)
        for table in metadata_welcome_message.sorted_tables:
            if not await conn.run_sync(lambda sync_conn: inspector.has_table(table.name)):
                await conn.run_sync(metadata_welcome_message.create_all)
                print(f"Created table {table.name}")
            else:
                logger.info(f"Table {table.name} already exists.")
