"""
Logging Utility
===============

Centralized logging configuration using Loguru.
Provides structured logging with file rotation and
console output formatting.
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_settings


def setup_logger() -> None:
    """
    Configure the application logger.

    Sets up:
    - Console output with colored formatting
    - File output with rotation and retention
    - Structured logging format
    """
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=settings.log.level,
        colorize=True,
    )

    # Ensure log directory exists
    log_dir = Path(settings.log.dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler with rotation
    logger.add(
        log_dir / "signup_{time:YYYY-MM-DD}.log",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        level=settings.log.level,
        rotation=settings.log.rotation,
        retention=settings.log.retention,
        compression="zip",
        enqueue=True,  # Thread-safe
    )

    # Error-specific log file
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}\n{exception}"
        ),
        level="ERROR",
        rotation=settings.log.rotation,
        retention=settings.log.retention,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info("Logger initialized successfully")


def get_logger(name: str | None = None) -> Any:
    """
    Get a logger instance with optional context binding.

    Args:
        name: Optional name to bind to the logger context.

    Returns:
        Logger instance with bound context.
    """
    if name:
        return logger.bind(name=name)
    return logger


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.

    Usage:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.log.info("Doing something")
    """

    @property
    def log(self) -> Any:
        """Get a logger bound to the class name."""
        return logger.bind(name=self.__class__.__name__)
