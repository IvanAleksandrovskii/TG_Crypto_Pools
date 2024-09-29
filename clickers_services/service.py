import csv
import os
from datetime import datetime
from sqlalchemy import text, select
from sqlalchemy.exc import ProgrammingError

from core.models import Clicker
from core import logger
from core.models import db_helper


async def import_clickers_from_csv():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, 'data', 'ClickersList.csv')

    async for session in db_helper.session_getter():
        try:
            # Check if the table exists
            await session.execute(text(f"SELECT 1 FROM {Clicker.__tablename__} LIMIT 1"))
        except ProgrammingError:
            logger.info(f"Table {Clicker.__tablename__} does not exist. Skipping import.")
            return

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    # Check if a clicker with this name already exists
                    existing_clicker = await session.execute(
                        select(Clicker).where(Clicker.name == row['Clicker Name'])
                    )
                    existing_clicker = existing_clicker.scalar_one_or_none()

                    if existing_clicker:
                        logger.info(f"Clicker '{row['Clicker Name']}' already exists. Skipping.")
                        continue

                    clicker = Clicker(
                        name=row['Clicker Name'],
                        description=row['Description'],
                        time_spent=row['Time spent'],
                        link=row['Link'],
                        audience=row['Audience'],
                        coin=row['Coin'],
                        app_launch_date=parse_date(row['App launch date']),
                        token_launch_date=parse_date(row['Token launch date']),
                        telegram_channel=row['Telegram channel '].strip(),
                        partners=row['Partners'],
                        comment=row[''],
                        logo=None,
                    )
                    session.add(clicker)

                await session.commit()
                logger.info("Clickers imported successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error importing clickers: {str(e)}")
            raise  # Re-raise the exception for debugging

        finally:
            await session.close()


def parse_date(date_string):
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, '%d.%m.%Y').date()
    except ValueError:
        return None


async def init_clickers():
    await import_clickers_from_csv()
