import asyncio
import random

from core import logger
from .parse_defilama import parse_defilama
from .parse_validator_info import parse_validator_info
from core.config import settings


async def run_parsing_with_delay():

    min_min, min_max = settings.scheduler.offers_update_min_range
    await asyncio.sleep(random.randint(min_min, min_max))

    try:
        await parse_defilama()
    except Exception as e:
        logger.error(e)
    try:
        await parse_validator_info()
    except Exception as e:
        logger.error(e)
