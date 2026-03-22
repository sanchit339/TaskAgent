""" AI-powered scheduler that integrates with OpenClaw
Considers: work days, weekends, holidays, comp-offs, available time """
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field

# =============================================================================
# Logging Configuration
# =============================================================================
def setup_logger(name: str = "scheduler", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    
    file_handler = logging.FileHandler("scheduler.log")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    available: bool = True

@dataclass
class DailyRoutine:
    work_start: str = "09:00"  # e.g., "09:00"
    work_end: str = "18:00"   # e.g., "18:00"
    work_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Monday=0, Sunday=6
    lunch_start: str = "13:00"
    lunch_end: str = "14:00"
    sleep_start: str = "23:00"
    sleep_end: str = "07:00"

class SchedulerConfig:
    def __init__(self, config_path: str = "config.json"):
        logger.info(f"Loading scheduler config from: {config_path}")
        self.config_path = Path(config_path)
        self.routine = DailyRoutine()
        self.holidays: List[str] = []  # ISO format dates
        self.comp_offs: List[str] = []  # ISO format dates
        self.default_task_duration = 30  # minutes
        self.load()
    
    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                routine_data = data.get('routine', {})
                self.routine = DailyRoutine(
                    work_start=routine_data.get('work_start', '09:00'),
                    work_end=routine_data.get('work_end', '18:00'),
                    work_days=routine_data.get('work_days', [0, 1, 2, 3, 4]),
                    lunch_start=routine_data.get('lunch_start', '13:00'),
                    lunch_end=routine_data.get('lunch_end', '14:00'),
                    sleep_start=routine_data.get('sleep_start', '23:00'),
                    sleep_end=routine_data.get('sleep_end', '07:00')
                )
                self.holidays = data.get('holidays', [])
                self.comp_offs = data.get('comp_offs', [])
                self.default_task_duration = data.get('default_task_duration', 30)
                logger.info(f"Config loaded | holidays: {len(self.holidays)}, comp_offs: {len(self.comp_offs)}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            logger.info("No config file found, using defaults")

    def save(self):
        try:
            data = {
                'routine': {
                    'work_start': self.routine.work_start,
                    'work_end': self.routine.work_end,
                    'work_days': self.routine.work_days,
                    'lunch_start': self.routine.lunch_start,
                    'lunch_end': self.routine.lunch_end,
                    'sleep_start': self.routine.sleep_start,
                    'sleep_end': self.routine.sleep_end
                },
                'holidays': self.holidays,
                'comp_offs': self.comp_offs,
                'default_task_duration': self.default_task_duration
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Config saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def is_work_day(self, date: datetime) -> bool:
        """Check if date is a work day (considering holidays and comp-offs)"""
        date_str = date.strftime("%Y-%m-%d")
        
        # Check if it's a comp-off (treated as work day)
        if date_str in self.comp_offs:
            return True
        
        # Check if it's a holiday (not a work day)
        if date_str in self.holidays:
            return False
        
        # Check if it's a regular work day
        is_work = date.weekday() in self.routine.work_days
        logger.debug(f"is_work_day({date_str}): {is_work}")
        return is_work

    def is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday"""
        return date.strftime("%Y-%m-%d") in self.holidays

    def add_holiday(self, date: datetime, name: str = ""):
        """Add a holiday"""
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in self.holidays:
            self.holidays.append(date_str)
            self.save()
            logger.info(f"Added holiday: {date_str} ({name})")

    def add_comp_off(self, date: datetime):
        """Add a comp-off day (treated as work day)"""
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in self.comp_offs:
            self.comp_offs.append(date_str)
            self.save()
            logger.info(f"Added comp-off: {date_str}")

class AIScheduler:
    def __init__(self, task_manager, config: SchedulerConfig = None):
        logger.info("Initializing AIScheduler")
        self.task_manager = task_manager
        self.config = config or SchedulerConfig()
        logger.debug(f"Work days: {self.config.routine.work_days}")

    def get_available_slots(self, date: datetime, duration: int = 30) -> List[TimeSlot]:
        """Get available time slots for a given date"""
        logger.debug(f"Getting available slots for {date.date()}, duration: {duration}min")
        
        slots = []
        
        if not self.config.is_work_day(date):
            logger.debug(f"Skipping {date.date()} - not a work day")
            return slots  # No work on non-work days

        # Parse routine times
        work_start = datetime.strptime(self.config.routine.work_start, "%H:%M")
        work_end = datetime.strptime(self.config.routine.work_end, "%H:%M")
        lunch_start = datetime.strptime(self.config.routine.lunch_start, "%H:%M")
        lunch_end = datetime.strptime(self.config.routine.lunch_end, "%H:%M")

        # Create base slot for the day
        day_start = date.replace(hour=work_start.hour, minute=work_start.minute)
        day_end = date.replace(hour=work_end.hour, minute=work_end.minute)

        # Morning slot (before lunch)
        morning_end = date.replace(hour=lunch_start.hour, minute=lunch_start.minute)
        if morning_end > day_start:
            slots.append(TimeSlot(start=day_start, end=morning_end))

        # Afternoon slot (after lunch)
        afternoon_start = date.replace(hour=lunch_end.hour, minute=lunch_end.minute)
        if afternoon_start < day_end:
            slots.append(TimeSlot(start=afternoon_start, end=day_end))

        # Remove slots that have already passed
        now = datetime.now()
        slots = [s for s in slots if s.end > now]
        
        logger.debug(f"Found {len(slots)} available slots")
        return slots

    def find_best_slot(self, duration: int = 30, earliest_date: datetime = None) -> Optional[datetime]:
        """Find the best available slot for a task"""
        if earliest_date is None:
            earliest_date = datetime.now()
        
        logger.info(f"Finding best slot for {duration}min task, earliest: {earliest_date.date()}")
        
        # Check the next 14 days
        for i in range(14):
            check_date = earliest_date + timedelta(days=i)
            
            if not self.config.is_work_day(check_date):
                logger.debug(f"Skipping {check_date.date()} - not a work day")
                continue
            
            slots = self.get_available_slots(check_date, duration)
            
            for slot in slots:
                slot_duration = (slot.end - slot.start).total_seconds() / 60
                if slot_duration >= duration:
                    logger.info(f"Found slot: {slot.start.strftime('%Y-%m-%d %H:%M')}")
                    return slot.start
        
        logger.warning(f"No available slot found for {duration}min task")
        return None

    def schedule_task(self, task_id: str, scheduled_time: datetime = None) -> bool:
        """Manually schedule a task or auto-schedule"""
        logger.info(f"Scheduling task: {task_id}")
        
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        if scheduled_time is None:
            # Auto-schedule
            scheduled_time = self.find_best_slot(
                task.estimated_duration, 
                task.due_date
            )
            if scheduled_time:
                logger.info(f"Auto-scheduled task {task_id} for {scheduled_time}")
            else:
                logger.warning(f"Could not find slot for task {task_id}")
        
        if scheduled_time:
            self.task_manager.update_task(task_id, scheduled_time=scheduled_time)
            return True
        
        return False

    def get_daily_schedule(self, date: datetime = None) -> List[Dict]:
        """Get the schedule for a specific day"""
        if date is None:
            date = datetime.now()
        
        logger.debug(f"Getting daily schedule for {date.date()}")
        
        try:
            tasks = self.task_manager.get_tasks(due_today=True, completed=False)
        except AttributeError as e:
            logger.error(f"task_manager missing get_tasks method: {e}")
            return []

        # Sort by priority and scheduled time
        try:
            tasks.sort(key=lambda t: (
                -getattr(t.priority, 'value', 0), 
                t.scheduled_time or datetime.max
            ))
        except Exception as e:
            logger.warning(f"Error sorting tasks: {e}")

        schedule = []
        current_time = datetime.now()
        available_slots = self.get_available_slots(date)

        for task in tasks:
            if task.scheduled_time:
                schedule.append({
                    "time": task.scheduled_time.strftime("%H:%M"),
                    "task": task.title,
                    "duration": task.estimated_duration,
                    "priority": getattr(task.priority, 'name', 'NONE'),
                    "project": task.project
                })

        logger.debug(f"Daily schedule: {len(schedule)} tasks")
        return schedule

    def suggest_schedule(self) -> str:
        """Generate a natural language schedule suggestion"""
        logger.debug("Generating schedule suggestion")
        
        today = datetime.now()
        schedule = self.get_daily_schedule(today)
        
        try:
            overdue = self.task_manager.get_overdue_tasks()
        except AttributeError:
            logger.warning("task_manager missing get_overdue_tasks method")
            overdue = []

        suggestions = []

        if overdue:
            suggestions.append(f"⚠️ You have {len(overdue)} overdue task(s)!")

        if schedule:
            suggestions.append("\n📅 Today's Schedule:")
            for item in schedule:
                emoji = "🔴" if item["priority"] == "URGENT" else "🟡" if item["priority"] == "HIGH" else "🟢"
                suggestions.append(f" {emoji} {item['time']} - {item['task']} ({item['duration']}min)")
        else:
            suggestions.append("\n✅ No tasks scheduled for today!")

        result = "\n".join(suggestions)
        logger.debug(f"Suggestion generated: {len(result)} chars")
        return result