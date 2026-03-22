import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json
from pathlib import Path

# Import the logger from __init__.py
from . import logger

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
    priority: Optional[str] = "MEDIUM"
    due_date: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    recurrence: Optional[str] = None
    estimated_duration: int = 30
    
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
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat()
        }
    
    def to_summary(self) -> str:
        """Get a summary string of the task."""
        status = "✓" if self.completed else " "
        return f"[{status}] {self.title} ({self.project})"


# =============================================================================
# Task Manager Class
# =============================================================================

class TaskManager:
    """Manages tasks with logging support."""
    
    def __init__(self, storage_path: str = "package_tasks.json"):
        """Initialize the TaskManager."""
        logger.info(f"Initializing TaskManager with storage: {storage_path}")
        self.storage_path = Path(storage_path)
        self.tasks: List[Task] = []
        self.projects = {"Inbox", "Personal", "Work", "Urgent"}
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
            logger.warning(f"Unknown project '{project}', using 'Inbox'")
            project = "Inbox"
        
        task = Task(title=title, project=project, **kwargs)
        self.tasks.append(task)
        self.save()
        
        logger.info(f"Task added with ID: {task.id}")
        return task
    
    def create_task(self, title: str, description: str = "", project: str = "Inbox", 
                    due_date=None, priority=None, labels=None, recurrence=None, 
                    estimated_duration: int = 30) -> Task:
        """Create a new task (alias for add_task with more options)."""
        logger.info(f"Creating task: '{title}' in project '{project}'")
        
        if project not in self.projects:
            logger.warning(f"Unknown project '{project}', using 'Inbox'")
            project = "Inbox"
        
        task = Task(
            title=title,
            description=description,
            project=project,
            priority=priority,
            due_date=due_date,
            labels=labels or [],
            recurrence=recurrence,
            estimated_duration=estimated_duration
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
    
    def get_tasks(self, project: str = None, completed: Optional[bool] = None, due_today: bool = False, overdue: bool = False, high_priority: bool = False) -> List[Task]:
        """Get tasks with optional filters."""
        logger.debug(f"Getting tasks | project={project}, completed={completed}, due_today={due_today}, overdue={overdue}, high_priority={high_priority}")
        
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
            tasks = [t for t in tasks if t.due_date and t.due_date < now and not t.completed]
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
    
    def get_projects(self) -> List[str]:
        """Get list of all projects."""
        logger.debug("Getting project list")
        return list(self.projects)