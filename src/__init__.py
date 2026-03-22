"""
Task Manager - OpenClaw Integration
A task and project management system that works as a local tool via stdio mode
and provides REST API endpoints for task CRUD, scheduling, and reminders.
"""

from src.task_manager import TaskManager, Priority, Task
from src.logging_utils import logger
from src.constants import (
    DEFAULT_PROJECTS,
    DEFAULT_PRIORITIES,
    DEFAULT_REMINDER_TIMES,
    DEFAULT_WORK_HOURS,
    DEFAULT_HOLIDAYS,
)
from src.api_utils import success_response, error_response

__version__ = "1.0.0"
__all__ = [
    "TaskManager",
    "Priority",
    "Task",
    "logger",
    "DEFAULT_PROJECTS",
    "DEFAULT_PRIORITIES",
    "DEFAULT_REMINDER_TIMES",
    "DEFAULT_WORK_HOURS",
    "DEFAULT_HOLIDAYS",
    "success_response",
    "error_response",
]