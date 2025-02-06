
import logging
from logging.handlers import RotatingFileHandler
from src.logger import get_logger
from io import StringIO
from pathlib import Path
from datetime import datetime


def test_logger_creation():
    logger_name = "test_logger"
    logger = get_logger(logger_name)

    assert logger.name == logger_name

    log_dir = Path("logs") / logger_name
    assert log_dir.exists()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"{logger_name}_{timestamp}.log"
    assert log_file.exists()


def test_logger_handlers():
    logger_name = "test_logger"
    logger = get_logger(logger_name)

    handlers = logger.handlers

    assert len(handlers) > 0

    console_handler = next(
        (h for h in handlers if isinstance(h, logging.StreamHandler)), None
    )
    file_handler = next(
        (h for h in handlers if isinstance(h, RotatingFileHandler)), None
    )

    assert console_handler is not None
    assert file_handler is not None


def test_logger_level():
    logger_name = "test_logger"
    logger = get_logger(logger_name)

    log_capture = StringIO()
    console_handler = logging.StreamHandler(log_capture)
    logger.addHandler(console_handler)

    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")

    log_capture.seek(0)
    logs = log_capture.read()

    assert "This is a debug message." in logs
    assert "This is an info message." in logs
    assert "This is a warning message." in logs
