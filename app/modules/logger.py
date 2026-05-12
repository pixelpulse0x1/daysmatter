"""Application logging with rotating file handler and debug toggle."""
import os
import logging
from logging.handlers import RotatingFileHandler
from app import DATA_DIR

LOG_DIR = os.path.join(DATA_DIR, "log")
_logger = None


def get_logger():
    """Return the application logger. Lazily initialized."""
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "app.log")

    _logger = logging.getLogger("daysmatter")
    _logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(handler)
    return _logger


def is_debug_enabled():
    """Check if debug_logging is enabled in settings."""
    try:
        import json
        settings_path = os.path.join(DATA_DIR, "json", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            return settings.get("debug_logging", False)
    except Exception:
        pass
    return False


def log(level, msg):
    """Log a message if debug mode is enabled."""
    if not is_debug_enabled():
        return
    logger = get_logger()
    if level == "debug":
        logger.debug(msg)
    elif level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
