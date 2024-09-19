from core import logger
from .parse_defilama import parse_defilama
from .parse_validator_info import parse_validator_info


async def run_parsing():
    # try:
    #     await parse_defilama()
    # except Exception as e:
    #     logger.error(e)
    try:
        await parse_validator_info()
    except Exception as e:
        logger.error(e)
