import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import json
from pathlib import Path

# Import constants directly from their modules (avoid circular import)
from .constants import DEFAULT_PROJECTS, DEFAULT_PRIORITY, DEFAULT_ESTIMATED_DURATION

# Import logger from logging_utils directly
from .logging_utils import setup_logger

logger = setup_logger("task_manager")

# =============================================================================
# Enums
# =============================================================================


class Priority:
    """Task priority levels"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

    @classmethod
    def from_string(cls, s: str):
        """Convert string to Priority"""
        return getattr(cls, s.upper(), cls.MEDIUM)


class RecurrencePattern:
    """Task recurrence patterns"""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    WEEKDAYS = "WEEKDAYS"

    @classmethod
    def from_string(cls, s: str):
        """Convert string to RecurrencePattern"""
        return getattr(cls, s.upper(), None)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Task:
    """Represents a task in the task manager."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    project: str = "Inbox"
    labels: List[str] = field(default_factory=list)
    priority: Optional[str] = DEFAULT_PRIORITY
    due_date: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    recurrence: Optional[str] = None
    estimated_duration: int = DEFAULT_ESTIMATED_DURATION
    scheduled_time: Optional[datetime] = None
    reminders: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Convert string dates to datetime objects after initialization."""
        # Parse due_date if it's a string
        if isinstance(self.due_date, str):
            self.due_date = Task.parse_datetime(self.due_date)

        # Parse completed_at if it's a string
        if isinstance(self.completed_at, str):
            self.completed_at = Task.parse_datetime(self.completed_at)

        # Parse created_at if it's a string
        if isinstance(self.created_at, str):
            self.created_at = Task.parse_datetime(self.created_at)
            if self.created_at is None:
                # Fallback to now if parsing fails
                self.created_at = datetime.now()

        # Parse scheduled_time if it's a string
        if isinstance(self.scheduled_time, str):
            self.scheduled_time = Task.parse_datetime(self.scheduled_time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "labels": self.labels,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "created_at": self.created_at.isoformat(),
            "recurrence": self.recurrence,
            "estimated_duration": self.estimated_duration,
            "scheduled_time": self.scheduled_time.isoformat()
            if self.scheduled_time
            else None,
            "reminders": self.reminders,
        }

    def to_summary(self) -> str:
        """Get a summary string of the task."""
        status = "✓" if self.completed else " "
        return f"[{status}] {self.title} ({self.project})"

    @staticmethod
    def parse_datetime(value):
        """Parse datetime from various formats (string, datetime, or None)."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try parsing ISO format first
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                # Try common formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
        return None


@dataclass
class Reminder:
    """Represents a reminder for a task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    reminder_time: Optional[datetime] = None
    notified: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert reminder to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "reminder_time": self.reminder_time.isoformat()
            if self.reminder_time
            else None,
            "notified": self.notified,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Task Manager Class
# =============================================================================


class TaskManager:
    """Manages tasks with logging support."""

    def __init__(self, storage_path: str = "my_tasks.json"):
        """Initialize the TaskManager."""
        logger.info(f"Initializing TaskManager with storage: {storage_path}")
        self.storage_path = Path(storage_path)
        self.tasks: List[Task] = []
        self.projects = set(DEFAULT_PROJECTS)  # Use set() to allow dynamic additions
        self.load()
        logger.info(f"TaskManager ready | {len(self.tasks)} tasks loaded")

    def load(self) -> None:
        """Load tasks from storage file."""
        if not self.storage_path.exists():
            logger.info("No existing task file found, starting fresh")
            return

        try:
            data = json.loads(self.storage_path.read_text())
            self.tasks = [Task(**task_data) for task_data in data]
            logger.info(f"Loaded {len(self.tasks)} tasks from {self.storage_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted task file: {e}")
            self.tasks = []
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
            self.tasks = []

    def save(self) -> None:
        """Save tasks to storage file."""
        try:
            data = [task.to_dict() for task in self.tasks]
            self.storage_path.write_text(json.dumps(data, indent=2, default=str))
            logger.debug(f"Saved {len(self.tasks)} tasks to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
            raise

    def add_task(self, title: str, project: str = "Inbox", **kwargs) -> Task:
        """Add a new task."""
        logger.info(f"Adding task: '{title}' to project '{project}'")

        if project not in self.projects:
            logger.info(f"Auto-creating project: {project}")
            self.projects.add(project)

        task = Task(title=title, project=project, **kwargs)
        self.tasks.append(task)
        self.save()

        logger.info(f"Task added with ID: {task.id}")
        return task

    def create_task(
        self,
        title: str,
        description: str = "",
        project: str = "Inbox",
        due_date=None,
        priority=None,
        labels=None,
        recurrence=None,
        estimated_duration: int = DEFAULT_ESTIMATED_DURATION,
    ) -> Task:
        """Create a new task (alias for add_task with more options)."""
        logger.info(f"Creating task: '{title}' in project '{project}'")

        if project not in self.projects:
            logger.info(f"Auto-creating project: {project}")
            self.projects.add(project)

        task = Task(
            title=title,
            description=description,
            project=project,
            priority=priority,
            due_date=due_date,
            labels=labels or [],
            recurrence=recurrence,
            estimated_duration=estimated_duration,
        )
        self.tasks.append(task)
        self.save()

        logger.info(f"Task created with ID: {task.id}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        logger.debug(f"Fetching task: {task_id}")
        task = next((t for t in self.tasks if t.id == task_id), None)

        if not task:
            logger.warning(f"Task not found: {task_id}")

        return task

    def get_tasks(
        self,
        project: str = None,
        completed: Optional[bool] = None,
        due_today: bool = False,
        overdue: bool = False,
        high_priority: bool = False,
    ) -> List[Task]:
        """Get tasks with optional filters."""
        logger.debug(
            f"Getting tasks | project={project}, completed={completed}, due_today={due_today}, overdue={overdue}, high_priority={high_priority}"
        )

        tasks = self.tasks

        if project:
            tasks = [t for t in tasks if t.project == project]
            logger.debug(f"Filtered by project '{project}': {len(tasks)} tasks")

        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
            logger.debug(f"Filtered by completed={completed}: {len(tasks)} tasks")

        if due_today:
            today = datetime.now().date()
            tasks = [t for t in tasks if t.due_date and t.due_date.date() == today]
            logger.debug(f"Filtered by due_today: {len(tasks)} tasks")

        if overdue:
            now = datetime.now()
            tasks = [
                t for t in tasks if t.due_date and t.due_date < now and not t.completed
            ]
            logger.debug(f"Filtered by overdue: {len(tasks)} tasks")

        if high_priority:
            tasks = [t for t in tasks if t.priority in ("HIGH", "URGENT")]
            logger.debug(f"Filtered by high_priority: {len(tasks)} tasks")

        return tasks

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        logger.info(f"Completing task: {task_id}")

        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot complete - task not found: {task_id}")
            return False

        task.completed = True
        task.completed_at = datetime.now()
        self.save()

        logger.info(f"Task completed: {task_id}")
        return True

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        logger.info(f"Deleting task: {task_id}")

        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot delete - task not found: {task_id}")
            return False

        self.tasks.remove(task)
        self.save()

        logger.info(f"Task deleted: {task_id}")
        return True

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields by ID."""
        logger.info(f"Updating task: {task_id} with {list(kwargs.keys())}")

        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot update - task not found: {task_id}")
            return False

        for key, value in kwargs.items():
            if hasattr(task, key):
                # Parse datetime strings
                if key in ("scheduled_time", "due_date", "completed_at") and isinstance(
                    value, str
                ):
                    value = Task.parse_datetime(value)
                setattr(task, key, value)
            else:
                logger.warning(f"Ignoring unknown task field: {key}")

        self.save()
        logger.info(f"Task updated: {task_id}")
        return True

    def batch_create_tasks(
        self, titles: List[str], project: str = "Inbox", due_date=None
    ) -> List[Task]:
        """Create multiple tasks at once."""
        logger.info(f"Batch creating {len(titles)} tasks in project '{project}'")
        tasks = []
        for title in titles:
            task = self.create_task(title=title, project=project, due_date=due_date)
            tasks.append(task)
        logger.info(f"Batch created {len(tasks)} tasks")
        return tasks

    def get_projects(self) -> List[str]:
        """Get list of all projects."""
        logger.debug("Getting project list")
        return list(self.projects)

    # =============================================================================
    # Reminder Methods
    # =============================================================================

    def add_reminder(self, task_id: str, reminder_time: datetime) -> Optional[Reminder]:
        """Add a reminder for a task."""
        logger.info(f"Adding reminder for task {task_id} at {reminder_time}")

        task = self.get_task(task_id)
        if not task:
            logger.warning(f"Cannot add reminder - task not found: {task_id}")
            return None

        reminder = Reminder(task_id=task_id, reminder_time=reminder_time)

        # Initialize reminders list if not exists
        if not hasattr(self, "reminders"):
            self.reminders: List[Reminder] = []

        self.reminders.append(reminder)
        self.save()

        logger.info(f"Reminder added: {reminder.id} for task {task_id}")
        return reminder

    def get_due_reminders(self) -> List[Tuple[Task, Reminder]]:
        """Get all reminders that are due (reminder_time <= now and not notified)."""
        logger.debug("Checking for due reminders")

        if not hasattr(self, "reminders"):
            self.reminders: List[Reminder] = []

        now = datetime.now()
        due_reminders: List[Tuple[Task, Reminder]] = []

        for reminder in self.reminders:
            if reminder.notified:
                continue

            if reminder.reminder_time and reminder.reminder_time <= now:
                task = self.get_task(reminder.task_id)
                if task:
                    due_reminders.append((task, reminder))
                    logger.debug(
                        f"Found due reminder: {reminder.id} for task {task.id}"
                    )

        return due_reminders

    def mark_reminder_notified(self, task_id: str, reminder_id: str) -> bool:
        """Mark a reminder as notified."""
        logger.info(f"Marking reminder {reminder_id} as notified for task {task_id}")

        if not hasattr(self, "reminders"):
            self.reminders: List[Reminder] = []

        for reminder in self.reminders:
            if reminder.id == reminder_id and reminder.task_id == task_id:
                reminder.notified = True
                self.save()
                logger.info(f"Reminder {reminder_id} marked as notified")
                return True

        logger.warning(f"Reminder not found: {reminder_id}")
        return False

    def get_reminders_for_task(self, task_id: str) -> List[Reminder]:
        """Get all reminders for a specific task."""
        if not hasattr(self, "reminders"):
            self.reminders: List[Reminder] = []

        return [r for r in self.reminders if r.task_id == task_id]

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder by ID."""
        if not hasattr(self, "reminders"):
            self.reminders: List[Reminder] = []

        for i, reminder in enumerate(self.reminders):
            if reminder.id == reminder_id:
                del self.reminders[i]
                self.save()
                logger.info(f"Reminder deleted: {reminder_id}")
                return True

        logger.warning(f"Reminder not found for deletion: {reminder_id}")
        return False
