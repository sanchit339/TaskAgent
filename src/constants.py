"""Centralized constants for the Task Manager package.

This module provides a single source of truth for all default values
used throughout the task manager system.
"""

# =============================================================================
# Project Defaults
# =============================================================================

DEFAULT_PROJECTS = frozenset({"Inbox", "Personal", "Work", "Urgent"})

# =============================================================================
# Task Defaults
# =============================================================================

DEFAULT_PRIORITY = "MEDIUM"
DEFAULT_ESTIMATED_DURATION = 30  # minutes

# =============================================================================
# Reminder System Defaults
# =============================================================================

DEFAULT_CHECK_INTERVAL = 30  # seconds
DEFAULT_REMINDER_TIMES = [5, 10, 15, 30]  # minutes before due

# =============================================================================
# Priority Levels
# =============================================================================

PRIORITY_LEVELS = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "URGENT": 3,
}

# Priority list for ordering
DEFAULT_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]

# =============================================================================
# Priority Symbols (for display)
# =============================================================================

PRIORITY_SYMBOLS = {
    "LOW": "↓",
    "MEDIUM": "·",
    "HIGH": "↑",
    "URGENT": "!",
}

# =============================================================================
# Work Schedule Defaults
# =============================================================================

DEFAULT_WORK_HOURS = {
    "start": "09:00",
    "end": "18:00",
}

DEFAULT_HOLIDAYS = []  # List of dates in YYYY-MM-DD format