"""Shared logging utilities - eliminates duplicate setup_logger() across modules"""
import logging
import os
from pathlib import Path

# OpenClaw log directory
OPENCLAW_LOG_DIR = Path.home() / ".openclaw" / "workspace" / "logs"

# Ensure log directory exists
OPENCLAW_LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = "main", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger.
    
    Args:
        name: Logger name, also used for log filename (e.g., "main" -> "main.log")
        level: Logging level (default: logging.INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers on reimport
    if logger.handlers:
        return logger

    # Console handler with formatted output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler for persistent logs in OpenClaw directory
    log_file = OPENCLAW_LOG_DIR / f"{name}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Default logger instance for the application
logger = setup_logger("task_manager", logging.INFO)