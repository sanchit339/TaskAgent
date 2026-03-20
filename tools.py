"""
OpenClaw Tool Definitions
These functions will be registered as tools for OpenClaw to call
"""

from typing import Optional, List
from datetime import datetime, timedelta
import json


class TaskTools:
    """Tools for OpenClaw integration"""

    def __init__(self, task_manager, scheduler, reminder_system):
        self.task_manager = task_manager
        self.scheduler = scheduler
        self.reminder_system = reminder_system

    # ==================== TASK CREATION TOOLS ====================

    def create_task(
        self,
        title: str,
        project: str = "Inbox",
        due_date: str = None,  # ISO format string
        due_time: str = None,
        priority: str = "MEDIUM",
        labels: List[str] = None,
        recurrence: str = None,
        estimated_duration: int = 30
    ) -> str:
        """Create a new task"""
        from task_manager import Priority, RecurrencePattern

        # Parse priority
        priority_enum = Priority[priority.upper()]

        # Parse due date
        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)
            if due_time:
                time_dt = datetime.strptime(due_time, "%H:%M").time()
                due_dt = due_dt.replace(hour=time_dt.hour, minute=time_dt.minute)

        # Parse recurrence
        recurrence_enum = None
        if recurrence:
            recurrence_enum = RecurrencePattern[recurrence.upper()]

        # Create task
        task = self.task_manager.create_task(
            title=title,
            project=project,
            due_date=due_dt,
            priority=priority_enum,
            labels=labels or [],
            recurrence=recurrence_enum,
            estimated_duration=estimated_duration
        )

        # Auto-schedule if due date is set
        if due_dt:
            self.scheduler.schedule_task(task.id)

        return f"✅ Task created: {title} (ID: {task.id})"

    def create_urgent_task(
        self,
        title: str,
        due_date: str = None,
        project: str = "Urgent"
    ) -> str:
        """Create a high-priority/urgent task"""
        return self.create_task(
            title=title,
            project=project,
            due_date=due_date,
            priority="URGENT"
        )

    def add_to_project(
        self,
        title: str,
        project: str,
        due_date: str = None
    ) -> str:
        """Add task to a specific project"""
        return self.create_task(
            title=title,
            project=project,
            due_date=due_date
        )

    def create_recurring_task(
        self,
        title: str,
        recurrence: str,  # DAILY, WEEKLY, MONTHLY, WEEKDAYS
        time: str = "10:00",
        project: str = "Inbox"
    ) -> str:
        """Create a recurring task"""
        today = datetime.now().date()
        due_dt = datetime.combine(today, datetime.strptime(time, "%H:%M").time())

        return self.create_task(
            title=title,
            project=project,
            due_date=due_dt.isoformat(),
            recurrence=recurrence,
            priority="MEDIUM"
        )

    # ==================== BATCH OPERATIONS ====================

    def batch_create_tasks(
        self,
        task_list: List[str],
        project: str = "Inbox",
        due_date: str = None
    ) -> str:
        """Create multiple tasks at once"""
        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)

        tasks = self.task_manager.batch_create_tasks(
            titles=task_list,
            project=project,
            due_date=due_dt
        )

        return f"✅ Created {len(tasks)} tasks in {project}"

    # ==================== TASK MANAGEMENT TOOLS ====================

    def complete_task(self, task_id: str = None, title: str = None) -> str:
        """Mark a task as completed"""
        if task_id:
            task = self.task_manager.complete_task(task_id)
            return f"✅ Completed: {task.title}"
        elif title:
            # Find by title
            tasks = self.task_manager.get_tasks(completed=False)
            for task in tasks:
                if title.lower() in task.title.lower():
                    self.task_manager.complete_task(task.id)
                    return f"✅ Completed: {task.title}"
            return f"❌ Task not found: {title}"
        return "❌ Please provide task_id or title"

    def delete_task(self, task_id: str) -> str:
        """Delete a task"""
        if self.task_manager.delete_task(task_id):
            return f"🗑️ Task deleted"
        return "❌ Task not found"

    def list_tasks(
        self,
        project: str = None,
        show_completed: bool = False,
        today: bool = False,
        overdue: bool = False,
        high_priority: bool = False
    ) -> str:
        """List tasks with filters"""
        tasks = self.task_manager.get_tasks(
            project=project,
            completed=None if show_completed else False,
            due_today=today,
            overdue=overdue,
            high_priority=high_priority
        )

        if not tasks:
            return "No tasks found"

        lines = ["📋 Tasks:"]
        for task in tasks:
            status = "✅" if task.completed else "⬜"
            priority_emoji = "🔴" if task.priority.value >= 3 else "🟡" if task.priority.value == 2 else "🟢"
            due_str = f" due {task.due_date.strftime('%m/%d %H:%M')}" if task.due_date else ""
            lines.append(f"  {status} {priority_emoji} {task.title} ({task.project}){due_str}")

        return "\n".join(lines)

    # ==================== REMINDER TOOLS ====================

    def set_reminder(
        self,
        task_id: str = None,
        title: str = None,
        minutes_before: int = 30,
        specific_time: str = None
    ) -> str:
        """Set a reminder for a task"""
        target_id = task_id

        if not target_id and title:
            # Find task by title
            tasks = self.task_manager.get_tasks(completed=False)
            for task in tasks:
                if title.lower() in task.title.lower():
                    target_id = task.id
                    break

        if not target_id:
            return "❌ Task not found"

        reminder_time = None
        if specific_time:
            reminder_time = datetime.fromisoformat(specific_time)

        reminder = self.reminder_system.set_reminder_for_task(
            target_id,
            minutes_before,
            reminder_time
        )

        if reminder:
            return f"🔔 Reminder set for {reminder.time.strftime('%Y-%m-%d %H:%M')}"
        return "❌ Could not set reminder"

    # ==================== SCHEDULING TOOLS ====================

    def get_schedule(self, date: str = None) -> str:
        """Get the schedule for a specific day"""
        if date:
            check_date = datetime.fromisoformat(date)
        else:
            check_date = datetime.now()

        schedule_data = self.scheduler.get_daily_schedule(check_date)

        if not schedule_data:
            return "No tasks scheduled for this day"

        lines = ["📅 Schedule:"]
        for item in schedule_data:
            lines.append(f"  {item['time']} - {item['task']} ({item['duration']}min) - {item['project']}")

        return "\n".join(lines)

    def get_schedule_suggestions(self) -> str:
        """Get AI schedule suggestions"""
        return self.scheduler.suggest_schedule()

    def update_routine(
        self,
        work_start: str = None,
        work_end: str = None,
        work_days: List[int] = None,
        lunch_start: str = None,
        lunch_end: str = None
    ) -> str:
        """Update daily routine settings"""
        config = self.scheduler.config

        if work_start:
            config.routine.work_start = work_start
        if work_end:
            config.routine.work_end = work_end
        if work_days:
            config.routine.work_days = work_days
        if lunch_start:
            config.routine.lunch_start = lunch_start
        if lunch_end:
            config.routine.lunch_end = lunch_end

        config.save()
        return "✅ Routine updated"

    def add_holiday(self, date: str, name: str = "") -> str:
        """Add a holiday"""
        holiday_date = datetime.fromisoformat(date)
        self.scheduler.config.add_holiday(holiday_date, name)
        return f"✅ Holiday added: {name or date}"

    def add_comp_off(self, date: str) -> str:
        """Add a comp-off day"""
        co_date = datetime.fromisoformat(date)
        self.scheduler.config.add_comp_off(co_date)
        return f"✅ Comp-off added: {date}"

    # ==================== PROJECT TOOLS ====================

    def list_projects(self) -> str:
        """List all projects"""
        projects = self.task_manager.projects
        lines = ["📁 Projects:", *[f"  - {p}" for p in sorted(projects)]]
        return "\n".join(lines)

    def get_task_details(self, task_id: str = None, title: str = None) -> str:
        """Get detailed info about a task"""
        if task_id:
            task = self.task_manager.get_task(task_id)
        elif title:
            tasks = self.task_manager.get_tasks(completed=False)
            task = None
            for t in tasks:
                if title.lower() in t.title.lower():
                    task = t
                    break
        else:
            return "❌ Please provide task_id or title"

        if not task:
            return "❌ Task not found"

        details = [
            f"📝 {task.title}",
            f"   Project: {task.project}",
            f"   Priority: {task.priority.name}",
            f"   Status: {'Completed' if task.completed else 'Pending'}",
        ]

        if task.due_date:
            details.append(f"   Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}")

        if task.labels:
            details.append(f"   Labels: {', '.join(task.labels)}")

        if task.reminders:
            reminder_times = [r.time.strftime('%H:%M') for r in task.reminders]
            details.append(f"   Reminders: {', '.join(reminder_times)}")

        if task.scheduled_time:
            details.append(f"   Scheduled: {task.scheduled_time.strftime('%H:%M')}")

        details.append(f"   Duration: {task.estimated_duration} min")

        return "\n".join(details)

    def get_all_tools(self) -> dict:
        """Return all tools in OpenClaw-compatible format"""
        return {
            "create_task": {
                "name": "create_task",
                "description": "Create a new task with optional due date, priority, and project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "project": {"type": "string", "description": "Project name (default: Inbox)"},
                        "due_date": {"type": "string", "description": "Due date ISO format"},
                        "due_time": {"type": "string", "description": "Due time HH:MM"},
                        "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"]},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "recurrence": {"type": "string", "enum": ["DAILY", "WEEKLY", "MONTHLY", "WEEKDAYS"]},
                        "estimated_duration": {"type": "integer"}
                    },
                    "required": ["title"]
                }
            },
            "create_urgent_task": {
                "name": "create_urgent_task",
                "description": "Create a high-priority urgent task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "due_date": {"type": "string", "description": "Due date ISO format"},
                        "project": {"type": "string", "description": "Project name (default: Urgent)"}
                    },
                    "required": ["title"]
                }
            },
            "add_to_project": {
                "name": "add_to_project",
                "description": "Add a task to a specific project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "project": {"type": "string", "description": "Project name"},
                        "due_date": {"type": "string", "description": "Due date ISO format"}
                    },
                    "required": ["title", "project"]
                }
            },
            "create_recurring_task": {
                "name": "create_recurring_task",
                "description": "Create a recurring task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "recurrence": {"type": "string", "enum": ["DAILY", "WEEKLY", "MONTHLY", "WEEKDAYS"]},
                        "time": {"type": "string", "description": "Time of day HH:MM (default 10:00)"},
                        "project": {"type": "string", "description": "Project name"}
                    },
                    "required": ["title", "recurrence"]
                }
            },
            "batch_create_tasks": {
                "name": "batch_create_tasks",
                "description": "Create multiple tasks at once",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_list": {"type": "array", "items": {"type": "string"}},
                        "project": {"type": "string", "description": "Project name"},
                        "due_date": {"type": "string", "description": "Due date ISO format"}
                    },
                    "required": ["task_list"]
                }
            },
            "complete_task": {
                "name": "complete_task",
                "description": "Mark a task as completed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID"},
                        "title": {"type": "string", "description": "Task title to find and complete"}
                    }
                }
            },
            "delete_task": {
                "name": "delete_task",
                "description": "Delete a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID to delete"}
                    },
                    "required": ["task_id"]
                }
            },
            "list_tasks": {
                "name": "list_tasks",
                "description": "List tasks with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Filter by project"},
                        "show_completed": {"type": "boolean", "description": "Show completed tasks"},
                        "today": {"type": "boolean", "description": "Show tasks due today"},
                        "overdue": {"type": "boolean", "description": "Show overdue tasks"},
                        "high_priority": {"type": "boolean", "description": "Show high priority tasks"}
                    }
                }
            },
            "set_reminder": {
                "name": "set_reminder",
                "description": "Set a reminder for a task (unlimited reminders!)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID"},
                        "title": {"type": "string", "description": "Task title to find"},
                        "minutes_before": {"type": "integer", "description": "Minutes before due time"},
                        "specific_time": {"type": "string", "description": "Specific reminder time ISO format"}
                    }
                }
            },
            "get_schedule": {
                "name": "get_schedule",
                "description": "Get the schedule for a specific day",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date ISO format (default: today)"}
                    }
                }
            },
            "get_schedule_suggestions": {
                "name": "get_schedule_suggestions",
                "description": "Get AI-powered schedule suggestions"
            },
            "update_routine": {
                "name": "update_routine",
                "description": "Update daily routine settings",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "work_start": {"type": "string", "description": "Work start time HH:MM"},
                        "work_end": {"type": "string", "description": "Work end time HH:MM"},
                        "work_days": {"type": "array", "items": {"type": "integer"}, "description": "Work days 0=Mon, 6=Sun"},
                        "lunch_start": {"type": "string", "description": "Lunch start time HH:MM"},
                        "lunch_end": {"type": "string", "description": "Lunch end time HH:MM"}
                    }
                }
            },
            "add_holiday": {
                "name": "add_holiday",
                "description": "Add a holiday (scheduler will avoid these dates)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date ISO format"},
                        "name": {"type": "string", "description": "Holiday name"}
                    },
                    "required": ["date"]
                }
            },
            "add_comp_off": {
                "name": "add_comp_off",
                "description": "Add a compensatory off day (treated as work day)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date ISO format"}
                    },
                    "required": ["date"]
                }
            },
            "list_projects": {
                "name": "list_projects",
                "description": "List all available projects"
            },
            "get_task_details": {
                "name": "get_task_details",
                "description": "Get detailed information about a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID"},
                        "title": {"type": "string", "description": "Task title to find"}
                    }
                }
            }
        }
