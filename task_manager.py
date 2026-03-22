from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import uuid
import json
from datetime import datetime

# ... existing imports ...

# =============================================================================
# JSON API Response Helpers
# =============================================================================

def success_response(
    data: Any = None,
    message: str = "OK",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Standard success envelope for API responses."""
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    if meta:
        response["meta"] = meta
    return response


def error_response(
    message: str,
    code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Standard error envelope for API responses."""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        response["error"]["details"] = details
    return response


def legacy_result_response(result: Any, **kwargs) -> Dict[str, Any]:
    """Wrapper for legacy {"result": ...} responses - maintains compatibility."""
    return {"result": result, **kwargs}


# ... existing Priority and RecurrencePattern enums ...

@dataclass
class Task:
    # ... existing fields ...
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    project: str = "Inbox"
    labels: List[str] = field(default_factory=list)
    priority: Any = None  # Will be set after Priority is defined
    due_date: Optional[datetime] = None
    due_time: Optional[datetime] = None
    recurrence: Any = None  # Will be set after RecurrencePattern
    recurrence_end: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    reminders: List[Any] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    estimated_duration: int = 30

    # ... existing methods ...
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project": self.project,
            "labels": self.labels,
            "priority": self.priority.name if hasattr(self.priority, 'name') else str(self.priority),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "recurrence": self.recurrence.value if self.recurrence and hasattr(self.recurrence, 'value') else str(self.recurrence) if self.recurrence else None,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "reminders": [{"time": r.time.isoformat(), "notified": r.notified} for r in self.reminders],
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "estimated_duration": self.estimated_duration
        }

    def to_compact_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "priority": self.priority.name if hasattr(self.priority, 'name') else str(self.priority),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed
        }

    def to_summary(self) -> str:
        status = "✓" if self.completed else " "
        priority_symbol = {"LOW": "↓", "MEDIUM": "·", "HIGH": "↑", "URGENT": "!"}
        p = self.priority.name if hasattr(self.priority, 'name') else str(self.priority)
        return f"[{status}] {priority_symbol.get(p, '·')} {self.title} ({self.project})"


# ... existing TaskManager class ...

# =============================================================================
# API Endpoint Helpers (use with TaskManager)
# =============================================================================

class TaskAPIMixin:
    """Mixin providing standardized API responses for Task operations."""
    
    def _wrap_task_response(self, task: Task) -> Dict[str, Any]:
        """Wrap single task in success envelope."""
        return success_response(data=task.to_dict())
    
    def _wrap_task_list_response(self, tasks: List[Task], meta: Optional[Dict] = None) -> Dict[str, Any]:
        """Wrap task list in success envelope with optional metadata."""
        return success_response(
            data=[t.to_compact_dict() for t in tasks],
            meta=meta or {"count": len(tasks)}
        )
    
    def _wrap_error(self, message: str, code: str = "TASK_ERROR") -> Dict[str, Any]:
        return error_response(message=message, code=code)
    
    # Example API methods using the helpers
    def get_task_api(self, task_id: str) -> Dict[str, Any]:
        """API endpoint: Get single task."""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return self._wrap_error(f"Task not found: {task_id}", "NOT_FOUND")
        return self._wrap_task_response(task)
    
    def list_tasks_api(self, project: Optional[str] = None, completed: Optional[bool] = None) -> Dict[str, Any]:
        """API endpoint: List tasks with optional filters."""
        tasks = self.tasks
        if project:
            tasks = [t for t in tasks if t.project == project]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return self._wrap_task_list_response(tasks, meta={"filters": {"project": project, "completed": completed}})
    
    def create_task_api(self, title: str, project: str = "Inbox", **kwargs) -> Dict[str, Any]:
        """API endpoint: Create task."""
        if project not in self.projects:
            return self._wrap_error(f"Invalid project: {project}", "INVALID_PROJECT")
        task = Task(title=title, project=project, **kwargs)
        self.tasks.append(task)
        self.save()
        return self._wrap_task_response(task)
    
    def delete_task_api(self, task_id: str) -> Dict[str, Any]:
        """API endpoint: Delete task."""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return self._wrap_error(f"Task not found: {task_id}", "NOT_FOUND")
        self.tasks.remove(task)
        self.save()
        return success_response(message="Task deleted", data={"id": task_id})


# Make TaskManager use the API mixin
class TaskManager(TaskAPIMixin):
    def __init__(self, storage_path: str = "tasks.json"):
        # ... existing init ...
        self.storage_path = Path(storage_path)
        self.tasks: List[Task] = []
        self.projects = {"Inbox", "Personal", "Work", "Urgent"}
        self.load()
    
    # ... existing load, _backup_corrupted_file, save methods ...