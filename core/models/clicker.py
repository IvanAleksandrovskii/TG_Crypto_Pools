from fastapi_storages.integrations.sqlalchemy import FileType
from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from core import clicker_storage


class Clicker(Base):
    name: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    time_spent: Mapped[str] = mapped_column(String, nullable=True)
    link: Mapped[str] = mapped_column(String, nullable=True)
    audience: Mapped[str] = mapped_column(String, nullable=True)
    coin: Mapped[str] = mapped_column(String, nullable=True)
    app_launch_date: Mapped[Date] = mapped_column(Date, nullable=True)
    token_launch_date: Mapped[Date] = mapped_column(Date, nullable=True)
    telegram_channel: Mapped[str] = mapped_column(String, nullable=True)
    partners: Mapped[str] = mapped_column(String, nullable=True)

    comment: Mapped[str] = mapped_column(String, nullable=True)
    logo = mapped_column(FileType(storage=clicker_storage))

    def __repr__(self):
        return f"Clicker(name='{self.name}', coin='{self.coin}')"

    def __str__(self):
        return self.name
