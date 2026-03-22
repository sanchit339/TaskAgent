"""
Task Management System - Todoist Clone
Supports: Tasks, Projects, Labels, Priorities, Recurring Tasks, Reminders
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
import uuid
import json
from pathlib import Path


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class RecurrencePattern(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"


@dataclass
class Reminder:
    id: str
    time: datetime
    notified: bool = False


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    project: str = "Inbox"
    labels: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    due_time: Optional[datetime] = None
    recurrence: Optional[RecurrencePattern] = None
    recurrence_end: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    reminders: List[Reminder] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None  # AI scheduled time
    estimated_duration: int = 30  # minutes

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "labels": self.labels,
            "priority": self.priority.name,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "recurrence": self.recurrence.value if self.recurrence else None,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "reminders": [{"time": r.time.isoformat(), "notified": r.notified} for r in self.reminders],
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "estimated_duration": self.estimated_duration
        }


class TaskManager:
    def __init__(self, storage_path: str = "tasks.json"):
        self.storage_path = Path(storage_path)
        self.tasks: List[Task] = []
        self.projects = {"Inbox", "Personal", "Work", "Urgent"}
        self.load()

    def load(self):
        """Load tasks from storage"""
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.tasks = [self._dict_to_task(t) for t in data.get('tasks', [])]
                self.projects = set(data.get('projects', ["Inbox", "Personal", "Work", "Urgent"]))

    def save(self):
        """Save tasks to storage"""
        data = {
            "tasks": [t.to_dict() for t in self.tasks],
            "projects": list(self.projects)
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _dict_to_task(self, d: dict) -> Task:
        """Convert dictionary to Task object"""
        task = Task(
            id=d['id'],
            title=d['title'],
            description=d.get('description', ''),
            project=d.get('project', 'Inbox'),
            labels=d.get('labels', []),
            priority=Priority[d.get('priority', 'MEDIUM')],
            completed=d.get('completed', False),
            created_at=datetime.fromisoformat(d.get('created_at', datetime.now().isoformat()))
        )

        if d.get('due_date'):
            task.due_date = datetime.fromisoformat(d['due_date'])
        if d.get('due_time'):
            task.due_time = datetime.fromisoformat(d['due_time'])
        if d.get('completed_at'):
            task.completed_at = datetime.fromisoformat(d['completed_at'])
        if d.get('recurrence'):
            task.recurrence = RecurrencePattern(d['recurrence'])
        if d.get('scheduled_time'):
            task.scheduled_time = datetime.fromisoformat(d['scheduled_time'])
        task.estimated_duration = d.get('estimated_duration', 30)

        # Load reminders
        for r in d.get('reminders', []):
            task.reminders.append(Reminder(
                id=str(uuid.uuid4()),
                time=datetime.fromisoformat(r['time']),
                notified=r.get('notified', False)
            ))

        return task

    # ==================== TASK CRUD ====================

    def create_task(
        self,
        title: str,
        description: str = "",
        project: str = "Inbox",
        due_date: Optional[datetime] = None,
        due_time: Optional[datetime] = None,
        priority: Priority = Priority.MEDIUM,
        labels: List[str] = None,
        recurrence: RecurrencePattern = None,
        recurrence_end: datetime = None,
        estimated_duration: int = 30
    ) -> Task:
        """Create a new task"""
        if project:
            self.projects.add(project)

        task = Task(
            title=title,
            description=description,
            project=project,
            due_date=due_date,
            due_time=due_time,
            priority=priority,
            labels=labels or [],
            recurrence=recurrence,
            recurrence_end=recurrence_end,
            estimated_duration=estimated_duration
        )

        self.tasks.append(task)
        self.save()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark task as completed"""
        task = self.get_task(task_id)
        if task:
            task.completed = True
            task.completed_at = datetime.now()

            # Handle recurring tasks
            if task.recurrence and task.due_date:
                self._create_recurring_instance(task)

            self.save()
        return task

    def _create_recurring_instance(self, original_task: Task):
        """Create next instance of recurring task"""
        if original_task.recurrence == RecurrencePattern.DAILY:
            new_due = original_task.due_date + timedelta(days=1)
        elif original_task.recurrence == RecurrencePattern.WEEKLY:
            new_due = original_task.due_date + timedelta(weeks=1)
        elif original_task.recurrence == RecurrencePattern.MONTHLY:
            new_due = original_task.due_date + timedelta(days=30)
        elif original_task.recurrence == RecurrencePattern.WEEKDAYS:
            new_due = original_task.due_date + timedelta(days=1)
            while new_due.weekday() >= 5:  # Skip weekends
                new_due += timedelta(days=1)
        else:
            return

        # Check if we've passed recurrence end
        if original_task.recurrence_end and new_due > original_task.recurrence_end:
            return

        # Create new task instance
        new_task = Task(
            title=original_task.title,
            project=original_task.project,
            due_date=new_due,
            due_time=original_task.due_time,
            priority=original_task.priority,
            labels=original_task.labels,
            recurrence=original_task.recurrence,
            recurrence_end=original_task.recurrence_end,
            estimated_duration=original_task.estimated_duration
        )
        self.tasks.append(new_task)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        task = self.get_task(task_id)
        if task:
            self.tasks.remove(task)
            self.save()
            return True
        return False

    def update_task(self, task_id: str, **kwargs) -> Task:
        """Update task attributes"""
        task = self.get_task(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.save()
        return task

    # ==================== REMINDERS ====================

    def add_reminder(self, task_id: str, reminder_time: datetime) -> Optional[Reminder]:
        """Add reminder to task - UNLIMITED unlike Todoist!"""
        task = self.get_task(task_id)
        if task:
            reminder = Reminder(id=str(uuid.uuid4()), time=reminder_time)
            task.reminders.append(reminder)
            self.save()
            return reminder
        return None

    def get_due_reminders(self) -> List[tuple]:
        """Get all reminders that are due"""
        now = datetime.now()
        due = []
        for task in self.tasks:
            if not task.completed:
                for reminder in task.reminders:
                    if not reminder.notified and reminder.time <= now:
                        due.append((task, reminder))
        return due

    def mark_reminder_notified(self, task_id: str, reminder_id: str):
        """Mark reminder as notified"""
        task = self.get_task(task_id)
        if task:
            for reminder in task.reminders:
                if reminder.id == reminder_id:
                    reminder.notified = True
                    self.save()
                    break

    # ==================== QUERIES ====================

    def get_tasks(
        self,
        project: str = None,
        completed: bool = None,
        due_today: bool = False,
        overdue: bool = False,
        high_priority: bool = False
    ) -> List[Task]:
        """Query tasks with filters"""
        results = self.tasks

        if project:
            results = [t for t in results if t.project == project]
        if completed is not None:
            results = [t for t in results if t.completed == completed]
        if due_today:
            today = datetime.now().date()
            results = [t for t in results if t.due_date and t.due_date.date() == today]
        if overdue:
            now = datetime.now()
            results = [t for t in results if not t.completed and t.due_date and t.due_date < now]
        if high_priority:
            results = [t for t in results if t.priority in [Priority.HIGH, Priority.URGENT] and not t.completed]

        return sorted(results, key=lambda t: (t.completed, -t.priority.value, t.due_date or datetime.max))

    def get_today_tasks(self) -> List[Task]:
        """Get all tasks due today"""
        return self.get_tasks(due_today=True)

    def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks"""
        return self.get_tasks(overdue=True)

    def get_inbox_tasks(self) -> List[Task]:
        """Get Inbox tasks"""
        return self.get_tasks(project="Inbox")

    # ==================== BATCH OPERATIONS ====================

    def batch_create_tasks(self, titles: List[str], project: str = "Inbox", due_date: datetime = None) -> List[Task]:
        """Create multiple tasks at once"""
        created_tasks = []
        for title in titles:
            task = self.create_task(
                title=title,
                project=project,
                due_date=due_date
            )
            created_tasks.append(task)
        return created_tasks

    def batch_complete_tasks(self, task_ids: List[str]) -> List[Task]:
        """Complete multiple tasks"""
        completed = []
        for task_id in task_ids:
            task = self.complete_task(task_id)
            completed.append(task)
        return completed
