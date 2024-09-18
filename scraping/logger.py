import logging
import os
from icecream import ic

from pythonjsonlogger import jsonlogger

from core import settings


# Setup logging
def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.

    :return: Configured logger
    """
    # Get the parent directory of the current working directory
    INIT_FLAG = "/app/.init_data_collected"

    # Check if the file exists
    file_exists = os.path.exists(INIT_FLAG)
    ic(f"INIT_FLAG file exists: {file_exists}")

    # Set log level based on the presence of the init flag file
    if settings.scraper.debug_conf or not file_exists:
        log_level_picked = logging.DEBUG
    else:
        log_level_picked = logging.WARNING

    print(f"Selected log level: {logging.getLevelName(log_level_picked)}")

    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(stream_formatter)

    new_logger = logging.getLogger("SCRAPING")
    new_logger.setLevel(log_level_picked)
    new_logger.addHandler(stream_handler)

    return new_logger


logger = setup_logging()
