from sqlalchemy import (
    Table, Column, String, Integer, DateTime, func, ForeignKey, MetaData, inspect, text, Boolean, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


metadata_logg = MetaData()

# Table for users log
tg_users = Table(
    'tg_users',
    metadata_logg,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('tg_user', BigInteger, nullable=False, unique=True, index=True),
    Column('username', String, nullable=True, unique=True, index=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
    Column('is_superuser', Boolean, default=False, nullable=False),
)

# Table for actions log
tg_users_log = Table(
    'tg_users_log',
    metadata_logg,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('tg_user', BigInteger, ForeignKey('tg_users.tg_user'), nullable=False, index=True),
    Column('url_log', String, nullable=True),  # Optional
    Column('context', JSON, nullable=True),  # Context with dict
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
)

Base_2 = declarative_base(metadata=metadata_logg)

class TgUser(Base_2):
    __table__ = tg_users
    logs = relationship("TgUserLog", back_populates="user", lazy='noload')

    id = __table__.c.id
    tg_user = __table__.c.tg_user
    username = __table__.c.username
    created_at = __table__.c.created_at
    is_superuser = __table__.c.is_superuser

    def __repr__(self):
        return f"{self.tg_user}"

    def __str__(self):
        return f"{self.tg_user}"


class TgUserLog(Base_2):
    __table__ = tg_users_log
    user = relationship("TgUser", back_populates="logs")

    id = __table__.c.id
    tg_user = __table__.c.tg_user
    url_log = __table__.c.url_log
    context = __table__.c.context
    created_at = __table__.c.created_at

    def __repr__(self):
        return f"(id={self.id}, url_log={self.url_log}, context={self.context}, created_at={self.created_at})"

    def __str__(self):
        return f"(id={self.id}, url_log={self.url_log}, context={self.context}, created_at={self.created_at})"


async def check_and_update_tables(engine):
    async with engine.begin() as conn:
        inspector = await conn.run_sync(inspect)

        # Check if tables exist and create them if necessary
        for table in metadata_logg.sorted_tables:
            if not await conn.run_sync(lambda sync_conn: inspector.has_table(table.name)):
                await conn.run_sync(lambda sync_conn: table.create(sync_conn))
                print(f"Created table {table.name}")
            else:
                # If the table exists, check and update its columns
                await add_missing_columns(engine, table)
                print(f"Checked and updated table {table.name}")


async def add_missing_columns(engine, table):
    async with engine.begin() as conn:
        inspector = await conn.run_sync(inspect)
        existing_columns = await conn.run_sync(lambda sync_conn: inspector.get_columns(table.name))
        existing_column_names = {col['name'] for col in existing_columns}
        for column in table.columns:
            if column.name not in existing_column_names:
                alter_stmt = text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column.type}")
                await conn.execute(alter_stmt)
                print(f"Added column {column.name} to table {table.name}")
