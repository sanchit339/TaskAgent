""" OpenClaw Tool Definitions These functions will be registered as tools for OpenClaw to call """
from typing import Any, Optional, List
from datetime import datetime, timedelta
import json
from .logging_utils import setup_logger
from .constants import DEFAULT_PRIORITY, DEFAULT_ESTIMATED_DURATION

logger = setup_logger("tools")


class TaskTools:
    """Tools for OpenClaw integration"""
    
    def __init__(self, task_manager: Any, scheduler: Any, reminder_system: Any) -> None:
        logger.info("Initializing TaskTools")
        self.task_manager = task_manager
        self.scheduler = scheduler
        self.reminder_system = reminder_system
        logger.debug("TaskTools initialized successfully")
    
    # ==================== TASK CREATION TOOLS ====================
    
    def create_task(
        self,
        title: str,
        description: str = "",
        project: str = "Inbox",
        due_date: str = None,  # ISO format string
        due_time: str = None,
        priority: str = DEFAULT_PRIORITY,
        labels: List[str] = None,
        recurrence: str = None,
        estimated_duration: int = DEFAULT_ESTIMATED_DURATION
    ) -> dict:
        """Create a new task"""
        logger.info(f"Creating task: '{title}' in project '{project}'")
        
        from .task_manager import Priority, RecurrencePattern
        
        # Parse priority
        priority_enum = Priority.from_string(priority)
        logger.debug(f"Priority: {priority_enum}")
        
        # Parse due date
        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)
            logger.debug(f"Due date: {due_dt}")
            if due_time:
                time_dt = datetime.strptime(due_time, "%H:%M").time()
                due_dt = due_dt.replace(hour=time_dt.hour, minute=time_dt.minute)
                logger.debug(f"Due time set: {due_dt}")
        
        # Parse recurrence
        recurrence_enum = None
        if recurrence:
            recurrence_enum = RecurrencePattern.from_string(recurrence)
            logger.debug(f"Recurrence: {recurrence_enum}")
        
        # Create task
        task = self.task_manager.create_task(
            title=title,
            description=description,
            project=project,
            due_date=due_dt,
            priority=priority,
            labels=labels or [],
            recurrence=recurrence,
            estimated_duration=estimated_duration
        )
        
        logger.info(f"Task created with ID: {task.id}")
        
        # Auto-schedule if due date is set
        if due_dt:
            logger.debug(f"Auto-scheduling task {task.id} for due date")
            self.scheduler.schedule_task(task.id)
        
        task_dict = {
            "id": task.id,
            "title": task.title,
            "project": task.project,
            "priority": task.priority,
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "labels": task.labels,
            "recurrence": task.recurrence,
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
        logger.info(f"Creating urgent task: '{title}'")
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
        logger.info(f"Adding task to project '{project}': '{title}'")
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
        logger.info(f"Creating recurring task: '{title}' with recurrence '{recurrence}'")
        today = datetime.now().date()
        due_dt = datetime.combine(today, datetime.strptime(time, "%H:%M").time())
        return self.create_task(
        title=title,
        project=project,
        due_date=due_dt.isoformat(),
        recurrence=recurrence,
        priority=DEFAULT_PRIORITY
        )
    
    # ==================== BATCH OPERATIONS ====================
    
    def batch_create_tasks(
        self,
        task_list: List[str],
        project: str = "Inbox",
        due_date: str = None
    ) -> dict:
        """Create multiple tasks at once"""
        logger.info(f"Batch creating {len(task_list)} tasks in project '{project}'")
        
        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)
        
        tasks = self.task_manager.batch_create_tasks(
            titles=task_list,
            project=project,
            due_date=due_dt
        )
        
        logger.info(f"Batch created {len(tasks)} tasks")
        
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
        logger.info(f"Completing task - ID: {task_id}, Title: {title}")
        
        if task_id:
            task = self.task_manager.complete_task(task_id)
            task_dict = {
                "id": task.id,
                "title": task.title,
                "project": task.project,
                "completed": task.completed
            }
            logger.info(f"Task completed: {task.id}")
            return {
                "task": task_dict,
                "message": f"✅ Completed: {task.title}"
            }
        elif title:
            # Find by title - require exact match (case-insensitive)
            tasks = self.task_manager.get_tasks(completed=False)
            matching_tasks = [task for task in tasks if title.lower() == task.title.lower()]
            
            if len(matching_tasks) == 0:
                logger.warning(f"Task not found by title: {title}")
                return {
                    "task": None,
                    "ok": False,
                    "message": f"❌ Task not found: {title}"
                }
            elif len(matching_tasks) > 1:
                # Multiple matches - require task_id to disambiguate
                task_list = [{"id": t.id, "title": t.title} for t in matching_tasks]
                logger.warning(f"Multiple tasks match title '{title}': {task_list}")
                return {
                    "task": None,
                    "ok": False,
                    "message": f"⚠️ Multiple tasks match '{title}'. Please use task_id to specify which one:\n" +
                               "\n".join([f"- {t.id}: {t.title}" for t in matching_tasks])
                }
            else:
                # Exact match found
                task = matching_tasks[0]
                self.task_manager.complete_task(task.id)
                task_dict = {
                    "id": task.id,
                    "title": task.title,
                    "project": task.project,
                    "completed": task.completed
                }
                logger.info(f"Task completed by title: {task.id}")
                return {
                    "task": task_dict,
                    "message": f"✅ Completed: {task.title}"
                }
        else:
            # Changed from bare return to else block
            logger.warning("complete_task called without task_id or title")
            return {
                "task": None,
                "ok": False,
                "message": "❌ Please provide task_id or title"
            }
    
    def delete_task(self, task_id: str) -> dict:
        """Delete a task"""
        logger.info(f"Deleting task: {task_id}")
        
        if self.task_manager.delete_task(task_id):
            logger.info(f"Task deleted: {task_id}")
            return {
                "ok": True,
                "message": f"🗑️ Task deleted (ID: {task_id})"
            }
        
        logger.warning(f"Task not found for deletion: {task_id}")
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
        logger.debug(f"Listing tasks - project: {project}, today: {today}, overdue: {overdue}, high_priority: {high_priority}")
        
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
                "priority": task.priority,
                "completed": task.completed,
                "due_date": task.due_date.isoformat() if task.due_date else None
            }
            task_list.append(task_dict)

        logger.debug(f"Returning {len(task_list)} tasks")
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
        logger.info(f"Setting reminder - task_id: {task_id}, title: {title}, minutes_before: {minutes_before}")
        
        target_id = task_id
        if not target_id and title:
            # Find task by title - require exact match (case-insensitive)
            tasks = self.task_manager.get_tasks(completed=False)
            matching_tasks = [task for task in tasks if title.lower() == task.title.lower()]
            
            if len(matching_tasks) == 0:
                logger.warning(f"Task not found for reminder: {title}")
                return {
                    "ok": False,
                    "message": f"❌ Task not found: {title}"
                }
            elif len(matching_tasks) > 1:
                # Multiple matches - require task_id to disambiguate
                task_list = [{"id": t.id, "title": t.title} for t in matching_tasks]
                logger.warning(f"Multiple tasks match title '{title}': {task_list}")
                return {
                    "ok": False,
                    "message": f"⚠️ Multiple tasks match '{title}'. Please use task_id to specify which one:\n" +
                               "\n".join([f"- {t.id}: {t.title}" for t in matching_tasks])
                }
            else:
                # Exact match found
                target_id = matching_tasks[0].id
    
        if not target_id:
            logger.warning(f"Task not found for reminder: {title or task_id}")
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
            logger.info(f"Reminder set for task {target_id} at {reminder.time}")
            return {
                "ok": True,
                "reminder_time": reminder.time.isoformat(),
                "message": f"🔔 Reminder set for {reminder.time.strftime('%Y-%m-%d %H:%M')}"
            }
        
        logger.warning(f"Could not set reminder for task {target_id}")
        return {
            "ok": False,
            "message": "❌ Could not set reminder"
        }
    
    # ==================== SCHEDULING TOOLS ====================
    
    def get_schedule(self, date: str = None) -> dict:
        """Get the schedule for a specific day"""
        logger.debug(f"Getting schedule for date: {date}")
        
        if date:
            check_date = datetime.fromisoformat(date)
        else:
            check_date = datetime.now()
        
        schedule_data = self.scheduler.get_daily_schedule(check_date)
        
        if not schedule_data:
            logger.debug("No tasks scheduled for the day")
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
        
        logger.debug(f"Returning {len(schedule_list)} scheduled tasks")
        return {
            "date": check_date.isoformat(),
            "schedule": schedule_list,
            "message": f"📅 Schedule for {check_date.strftime('%Y-%m-%d')}"
        }
    
    def get_schedule_suggestions(self) -> dict:
        """Get AI schedule suggestions"""
        logger.debug("Getting schedule suggestions")
        
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
        logger.info("Updating routine settings")
        
        config = self.scheduler.config
        if work_start:
            config.routine.work_start = work_start
            logger.debug(f"Work start set to: {work_start}")
        if work_end:
            config.routine.work_end = work_end
            logger.debug(f"Work end set to: {work_end}")
        if work_days:
            config.routine.work_days = work_days
            logger.debug(f"Work days set to: {work_days}")
        if lunch_start:
            config.routine.lunch_start = lunch_start
            logger.debug(f"Lunch start set to: {lunch_start}")
        if lunch_end:
            config.routine.lunch_end = lunch_end
            logger.debug(f"Lunch end set to: {lunch_end}")
        
        config.save()
        logger.info("Routine settings saved")
        
        return {
            "ok": True,
            "message": "✅ Routine updated"
        }
    
    def add_holiday(self, date: str, name: str = "") -> dict:
        """Add a holiday"""
        logger.info(f"Adding holiday: {date} - {name}")
        
        holiday_date = datetime.fromisoformat(date)
        self.scheduler.config.add_holiday(holiday_date, name)
        
        logger.info(f"Holiday added: {date}")
        return {
            "ok": True,
            "date": date,
            "name": name,
            "message": f"✅ Holiday added: {name or date}"
        }
    
    def add_comp_off(self, date: str) -> dict:
        """Add a comp-off day"""
        logger.info(f"Adding comp-off: {date}")
        
        co_date = datetime.fromisoformat(date)
        self.scheduler.config.add_comp_off(co_date)
        
        logger.info(f"Comp-off added: {date}")
        return {
            "ok": True,
            "date": date,
            "message": f"✅ Comp-off added: {date}"
        }
    
    # ==================== PROJECT TOOLS ====================
    
    def list_projects(self) -> dict:
        """List all projects"""
        logger.debug("Listing all projects")
        
        projects = self.task_manager.projects
        logger.debug(f"Found {len(projects)} projects")
        
        return {
            "projects": sorted(list(projects)),
            "message": f"📁 Projects: {', '.join(sorted(projects))}"
        }
    
    def get_task_details(self, task_id: str = None, title: str = None) -> dict:
        """Get detailed info about a task"""
        logger.debug(f"Getting task details - task_id: {task_id}, title: {title}")
    
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
            logger.warning("get_task_details called without task_id or title")
            return {
                "ok": False,
                "message": "❌ Please provide task_id or title"
            }
    
        if not task:
            logger.warning(f"Task not found: {task_id or title}")
            return {
                "ok": False,
                "message": "❌ Task not found"
            }
    
        details = {
            "id": task.id,
            "title": task.title,
            "project": task.project,
            "priority": task.priority,
            "status": "Completed" if task.completed else "Pending",
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "labels": task.labels,
            "estimated_duration": task.estimated_duration,
            "scheduled_time": task.scheduled_time.strftime('%H:%M') if task.scheduled_time else None,
            "reminders": [r.time.strftime('%H:%M') for r in task.reminders] if task.reminders else []
        }
        
        logger.debug(f"Returning details for task: {task.id}")
        return {
            "task": details,
            "message": f"📝 {task.title}"
        }
    
    def get_all_tools(self) -> dict:
        """Get list of all available tools"""
        logger.debug("Getting all tools")
        tools = [
            {"name": "create_task", "description": "Create a new task"},
            {"name": "create_urgent_task", "description": "Create an urgent task"},
            {"name": "add_to_project", "description": "Add task to a project"},
            {"name": "create_recurring_task", "description": "Create a recurring task"},
            {"name": "batch_create_tasks", "description": "Create multiple tasks at once"},
            {"name": "complete_task", "description": "Mark a task as completed"},
            {"name": "delete_task", "description": "Delete a task"},
            {"name": "list_tasks", "description": "List tasks with optional filters"},
            {"name": "set_reminder", "description": "Set a reminder for a task"},
            {"name": "get_schedule", "description": "Get schedule for a specific date"},
            {"name": "get_schedule_suggestions", "description": "Get AI schedule suggestions"},
            {"name": "update_routine", "description": "Update daily routine"},
            {"name": "add_holiday", "description": "Add a holiday"},
            {"name": "add_comp_off", "description": "Add a comp-off day"},
            {"name": "list_projects", "description": "List all projects"},
            {"name": "get_task_details", "description": "Get detailed task information"},
        ]
        return {
            "tools": tools,
            "count": len(tools),
        }