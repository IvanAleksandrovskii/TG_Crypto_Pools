import logging
from pythonjsonlogger import jsonlogger


# Setup logging
def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.

    :return: Configured logger
    """
    log_level = logging.DEBUG  # TODO: make it configurable or... check with flag and if just created run with info, then warning/error

    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(stream_formatter)

    new_logger = logging.getLogger("SCRAPERS")
    new_logger.setLevel(log_level)
    new_logger.addHandler(stream_handler)

    return new_logger


logger = setup_logging()
