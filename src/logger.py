
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

_root = None


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance
    :param name: Name of the logger instance
    """

    global _root

    LOGS_DIR = Path("logs")
    os.makedirs(LOGS_DIR, exist_ok=True)

    if _root is None:
        _root = logging.getLogger("root")

        LOGS_DIR = Path("logs")
        os.makedirs(LOGS_DIR, exist_ok=True)
        LOG_DIR = LOGS_DIR / Path("root")
        os.makedirs(LOG_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        LOG_FILE = os.path.join(LOG_DIR, f"root_{timestamp}.log")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        root_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        root_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        root_handler.setFormatter(formatter)
        _root.addHandler(console_handler)
        _root.addHandler(root_handler)
        _root.setLevel(logging.DEBUG)

        _root.debug("Root logger created.")

    if name == "root":
        return _root

    LOG_DIR = LOGS_DIR / Path(name)
    os.makedirs(LOG_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    LOG_FILE = os.path.join(LOG_DIR, f"{name}_{timestamp}.log")

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        logger.propagate = True

        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        # console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
