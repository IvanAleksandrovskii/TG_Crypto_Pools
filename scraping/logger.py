import logging
import os

from pythonjsonlogger import jsonlogger

from core import settings


# Setup logging
def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.

    :return: Configured logger
    """
    INIT_FLAG = "/app/.init_data_collected"

    # Set log level based on the presence of the init flag file
    if not settings.scraper.debug and os.path.exists(INIT_FLAG):
        log_level = logging.WARNING
    else:
        log_level = logging.DEBUG

    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(stream_formatter)

    new_logger = logging.getLogger("SCRAPING")
    new_logger.setLevel(log_level)
    new_logger.addHandler(stream_handler)

    return new_logger


logger = setup_logging()
