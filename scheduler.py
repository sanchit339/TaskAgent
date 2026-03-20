"""
AI-powered scheduler that integrates with OpenClaw
Considers: work days, weekends, holidays, comp-offs, available time
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    available: bool = True


@dataclass
class DailyRoutine:
    work_start: str = "09:00"      # e.g., "09:00"
    work_end: str = "18:00"        # e.g., "18:00"
    work_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Monday=0, Sunday=6
    lunch_start: str = "13:00"
    lunch_end: str = "14:00"
    sleep_start: str = "23:00"
    sleep_end: str = "07:00"


class SchedulerConfig:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.routine = DailyRoutine()
        self.holidays: List[str] = []  # ISO format dates
        self.comp_offs: List[str] = []  # ISO format dates
        self.default_task_duration = 30  # minutes
        self.load()

    def load(self):
        if self.config_path.exists():
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

    def save(self):
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
        return date.weekday() in self.routine.work_days

    def is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday"""
        return date.strftime("%Y-%m-%d") in self.holidays

    def add_holiday(self, date: datetime, name: str = ""):
        """Add a holiday"""
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in self.holidays:
            self.holidays.append(date_str)
            self.save()

    def add_comp_off(self, date: datetime):
        """Add a comp-off day (treated as work day)"""
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in self.comp_offs:
            self.comp_offs.append(date_str)
            self.save()


class AIScheduler:
    def __init__(self, task_manager, config: SchedulerConfig = None):
        self.task_manager = task_manager
        self.config = config or SchedulerConfig()

    def get_available_slots(self, date: datetime, duration: int = 30) -> List[TimeSlot]:
        """Get available time slots for a given date"""
        slots = []

        if not self.config.is_work_day(date):
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

        return slots

    def find_best_slot(self, duration: int = 30, earliest_date: datetime = None) -> Optional[datetime]:
        """Find the best available slot for a task"""
        if earliest_date is None:
            earliest_date = datetime.now()

        # Check the next 7 days
        for i in range(14):
            check_date = earliest_date + timedelta(days=i)

            if not self.config.is_work_day(check_date):
                continue

            slots = self.get_available_slots(check_date, duration)

            for slot in slots:
                slot_duration = (slot.end - slot.start).total_seconds() / 60
                if slot_duration >= duration:
                    # Found a suitable slot
                    return slot.start

        return None

    def schedule_task(self, task_id: str, scheduled_time: datetime = None) -> bool:
        """Manually schedule a task or auto-schedule"""
        task = self.task_manager.get_task(task_id)
        if not task:
            return False

        if scheduled_time is None:
            # Auto-schedule
            scheduled_time = self.find_best_slot(task.estimated_duration, task.due_date)

        if scheduled_time:
            self.task_manager.update_task(task_id, scheduled_time=scheduled_time)
            return True

        return False

    def get_daily_schedule(self, date: datetime = None) -> List[Dict]:
        """Get the schedule for a specific day"""
        if date is None:
            date = datetime.now()

        tasks = self.task_manager.get_tasks(due_today=True, completed=False)

        # Sort by priority and scheduled time
        tasks.sort(key=lambda t: (-t.priority.value, t.scheduled_time or datetime.max))

        schedule = []
        current_time = datetime.now()
        available_slots = self.get_available_slots(date)

        for task in tasks:
            if task.scheduled_time:
                schedule.append({
                    "time": task.scheduled_time.strftime("%H:%M"),
                    "task": task.title,
                    "duration": task.estimated_duration,
                    "priority": task.priority.name,
                    "project": task.project
                })

        return schedule

    def suggest_schedule(self) -> str:
        """Generate a natural language schedule suggestion"""
        today = datetime.now()
        schedule = self.get_daily_schedule(today)
        overdue = self.task_manager.get_overdue_tasks()

        suggestions = []

        if overdue:
            suggestions.append(f"⚠️ You have {len(overdue)} overdue task(s)!")

        if schedule:
            suggestions.append("\n📅 Today's Schedule:")
            for item in schedule:
                emoji = "🔴" if item["priority"] == "URGENT" else "🟡" if item["priority"] == "HIGH" else "🟢"
                suggestions.append(f"  {emoji} {item['time']} - {item['task']} ({item['duration']}min)")
        else:
            suggestions.append("\n✅ No tasks scheduled for today!")

        return "\n".join(suggestions)
