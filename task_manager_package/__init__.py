import logging
from pathlib import Path

# =============================================================================
# Logging Configuration
# =============================================================================

def setup_logger(name: str = "task_manager_package", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with both file and console handlers."""
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
    
    # File handler for persistent logs
    file_handler = logging.FileHandler("task_manager_package.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create module-level logger
logger = setup_logger()

# Log package initialization
logger.info("task_manager_package initialized")