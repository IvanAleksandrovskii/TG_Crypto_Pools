import re

from icecream import ic

import logging
from pythonjsonlogger import jsonlogger

from core import settings

ic.disable()
# ic.enable()


# Setup logging
def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.

    :return: Configured logger
    """
    log_level = logging.DEBUG if settings.run.debug else logging.INFO

    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(stream_formatter)

    # TODO: write some acceptable naming logic
    new_logger = logging.getLogger("MainLogger")
    new_logger.setLevel(log_level)
    new_logger.addHandler(stream_handler)

    # Hide too many logging information
    # class NoFaviconFilter(logging.Filter):
    #     def filter(self, record):
    #         return not any(x in record.getMessage() for x in ['favicon.ico', 'apple-touch-icon'])
    #
    # logging.getLogger("uvicorn").addFilter(NoFaviconFilter())
    # logging.getLogger("uvicorn.access").addFilter(NoFaviconFilter())
    # logging.getLogger("fastapi").addFilter(NoFaviconFilter())
    # logging.getLogger('httpx').setLevel(logging.WARNING)
    # logging.getLogger('httpcore').setLevel(logging.WARNING)

    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    if settings.run.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    return new_logger


ic("logger")
logger = ic(setup_logging())


# Debug WARNING
if settings.run.debug:
    logger.warning("DEBUG mode is on!")
    # Regex for login and password searching in URL
    masked_url = re.sub(r'(://[^:]+:)[^@]+(@)', r'\1******\2', settings.db.url)
    # DB URL
    logger.info("Database URL: %s", masked_url)

# Database ECHO WARNING
if settings.db.echo:
    logger.warning("Database ECHO is on!")
