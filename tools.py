""" OpenClaw Tool Definitions
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
        description: str = "",
        project: str = "Inbox",
        due_date: str = None,  # ISO format string
        due_time: str = None,
        priority: str = "MEDIUM",
        labels: List[str] = None,
        recurrence: str = None,
        estimated_duration: int = 30
    ) -> dict:
        """Create a new task"""
        from task_manager_package.task_manager import Priority, RecurrencePattern

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
            description=description,
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

        task_dict = {
            "id": task.id,
            "title": task.title,
            "project": task.project,
            "priority": task.priority.name,
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "labels": task.labels,
            "recurrence": task.recurrence.name if task.recurrence else None,
            "estimated_duration": task.estimated_duration
        }

        return {
            "task": task_dict,
            "message": f"✅ Task created: {title} (ID: {task.id})"
        }

    def create_urgent_task(
        self,
        title: str,
        due_date: str = None,
        project: str = "Urgent"
    ) -> dict:
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
    ) -> dict:
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
    ) -> dict:
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
    ) -> dict:
        """Create multiple tasks at once"""
        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)

        tasks = self.task_manager.batch_create_tasks(
            titles=task_list,
            project=project,
            due_date=due_dt
        )

        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "project": t.project
                }
                for t in tasks
            ],
            "count": len(tasks),
            "message": f"✅ Created {len(tasks)} tasks in {project}"
        }

    # ==================== TASK MANAGEMENT TOOLS ====================

    def complete_task(self, task_id: str = None, title: str = None) -> dict:
        """Mark a task as completed"""
        if task_id:
            task = self.task_manager.complete_task(task_id)
            task_dict = {
                "id": task.id,
                "title": task.title,
                "project": task.project,
                "completed": task.completed
            }
            return {
                "task": task_dict,
                "message": f"✅ Completed: {task.title}"
            }
        elif title:
            # Find by title
            tasks = self.task_manager.get_tasks(completed=False)
            for task in tasks:
                if title.lower() in task.title.lower():
                    self.task_manager.complete_task(task.id)
                    task_dict = {
                        "id": task.id,
                        "title": task.title,
                        "project": task.project,
                        "completed": task.completed
                    }
                    return {
                        "task": task_dict,
                        "message": f"✅ Completed: {task.title}"
                    }
            return {
                "task": None,
                "ok": False,
                "message": f"❌ Task not found: {title}"
            }
        else:  # Changed from bare return to else block
            return { "task": None, "ok": False, "message": "❌ Please provide task_id or title" }

    def delete_task(self, task_id: str) -> dict:
        """Delete a task"""
        if self.task_manager.delete_task(task_id):
            return {
                "ok": True,
                "message": f"🗑️ Task deleted (ID: {task_id})"
            }
        return {
            "ok": False,
            "message": "❌ Task not found"
        }

    def list_tasks(
        self,
        project: str = None,
        show_completed: bool = False,
        today: bool = False,
        overdue: bool = False,
        high_priority: bool = False,
        limit: int = None,
        offset: int = 0
    ) -> dict:
        """List tasks with filters, returning compact JSON structure"""
        tasks = self.task_manager.get_tasks(
            project=project,
            completed=None if show_completed else False,
            due_today=today,
            overdue=overdue,
            high_priority=high_priority
        )

        # Apply offset and limit
        if offset:
            tasks = tasks[offset:]
        if limit:
            tasks = tasks[:limit]

        # Build compact task list
        task_list = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "title": task.title,
                "project": task.project,
                "priority": task.priority.name,
                "completed": task.completed,
                "due_date": task.due_date.isoformat() if task.due_date else None
            }
            task_list.append(task_dict)

        return {"tasks": task_list, "total": len(task_list)}

    # ==================== REMINDER TOOLS ====================

    def set_reminder(
        self,
        task_id: str = None,
        title: str = None,
        minutes_before: int = 30,
        specific_time: str = None
    ) -> dict:
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
            return {
                "ok": False,
                "message": "❌ Task not found"
            }

        reminder_time = None
        if specific_time:
            reminder_time = datetime.fromisoformat(specific_time)

        reminder = self.reminder_system.set_reminder_for_task(
            target_id,
            minutes_before,
            reminder_time
        )

        if reminder:
            return {
                "ok": True,
                "reminder_time": reminder.time.isoformat(),
                "message": f"🔔 Reminder set for {reminder.time.strftime('%Y-%m-%d %H:%M')}"
            }
        
        return {
            "ok": False,
            "message": "❌ Could not set reminder"
        }

    # ==================== SCHEDULING TOOLS ====================

    def get_schedule(self, date: str = None) -> dict:
        """Get the schedule for a specific day"""
        if date:
            check_date = datetime.fromisoformat(date)
        else:
            check_date = datetime.now()

        schedule_data = self.scheduler.get_daily_schedule(check_date)

        if not schedule_data:
            return {
                "date": check_date.isoformat(),
                "schedule": [],
                "message": "No tasks scheduled for this day"
            }

        schedule_list = []
        for item in schedule_data:
            schedule_list.append({
                "time": item["time"],
                "task": item["task"],
                "duration": item["duration"],
                "project": item["project"]
            })

        return {
            "date": check_date.isoformat(),
            "schedule": schedule_list,
            "message": f"📅 Schedule for {check_date.strftime('%Y-%m-%d')}"
        }

    def get_schedule_suggestions(self) -> dict:
        """Get AI schedule suggestions"""
        suggestions = self.scheduler.suggest_schedule()
        return {
            "suggestions": suggestions,
            "message": "Here are schedule suggestions"
        }

    def update_routine(
        self,
        work_start: str = None,
        work_end: str = None,
        work_days: List[int] = None,
        lunch_start: str = None,
        lunch_end: str = None
    ) -> dict:
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

        return {
            "ok": True,
            "message": "✅ Routine updated"
        }

    def add_holiday(self, date: str, name: str = "") -> dict:
        """Add a holiday"""
        holiday_date = datetime.fromisoformat(date)
        self.scheduler.config.add_holiday(holiday_date, name)
        
        return {
            "ok": True,
            "date": date,
            "name": name,
            "message": f"✅ Holiday added: {name or date}"
        }

    def add_comp_off(self, date: str) -> dict:
        """Add a comp-off day"""
        co_date = datetime.fromisoformat(date)
        self.scheduler.config.add_comp_off(co_date)
        
        return {
            "ok": True,
            "date": date,
            "message": f"✅ Comp-off added: {date}"
        }

    # ==================== PROJECT TOOLS ====================

    def list_projects(self) -> dict:
        """List all projects"""
        projects = self.task_manager.projects
        
        return {
            "projects": sorted(list(projects)),
            "message": f"📁 Projects: {', '.join(sorted(projects))}"
        }

    def get_task_details(self, task_id: str = None, title: str = None) -> dict:
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
            return {
                "ok": False,
                "message": "❌ Please provide task_id or title"
            }

        if not task:
            return {
                "ok": False,
                "message": "❌ Task not found"
            }

        details = {
            "id": task.id,
            "title": task.title,
            "project": task.project,
            "priority": task.priority.name,
            "status": "Completed" if task.completed else "Pending",
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "labels": task.labels,
            "estimated_duration": task.estimated_duration,
            "scheduled_time": task.scheduled_time.strftime('%H:%M') if task.scheduled_time else None,
            "reminders": [r.time.strftime('%H:%M') for r in task.reminders] if task.reminders else []
        }

        return {
            "task": details,
            "message": f"📝 {task.title}"
        }