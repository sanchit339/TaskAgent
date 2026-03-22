""" Unlimited reminder system - No more 5 reminder limit! """
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, List
import os
import subprocess
import logging

# =============================================================================
# Logging Configuration
# =============================================================================

def setup_logger(name: str = "reminder", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    
    file_handler = logging.FileHandler("reminder.log")
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


class ReminderSystem:
    def __init__(self, task_manager, check_interval: int = 30):
        logger.info(f"Initializing ReminderSystem with check_interval={check_interval}s")
        self.task_manager = task_manager
        self.check_interval = check_interval
        self.running = False
        self.callbacks: List[Callable] = []
        logger.debug(f"ReminderSystem initialized with {len(self.callbacks)} callbacks")
    
    def add_callback(self, callback: Callable):
        """Add a callback function to be called when reminder triggers"""
        logger.info(f"Adding callback: {callback.__name__}")
        self.callbacks.append(callback)
    
    def notify(self, task, reminder):
        """Send notification for a reminder"""
        logger.info(f"Sending notification for task: {task.id} - {task.title}")
        message = f"🔔 Reminder: {task.title}"
        if task.due_date:
            message += f"\nDue: {task.due_date.strftime('%Y-%m-%d %H:%M')}"
        if task.project != "Inbox":
            message += f"\nProject: {task.project}"
        
        # Try different notification methods
        self._send_notification(message)
        
        # Call registered callbacks (for OpenClaw integration)
        for callback in self.callbacks:
            try:
                logger.debug(f"Calling callback: {callback.__name__}")
                callback(task, reminder)
            except Exception as e:
                logger.error(f"Callback error in {callback.__name__}: {e}")
        
        # Mark as notified
        self.task_manager.mark_reminder_notified(task.id, reminder.id)
        logger.info(f"Reminder notified for task: {task.id}")
    
    def _send_notification(self, message: str):
        """Send system notification"""
        logger.debug(f"Sending notification: {message[:50]}...")
        
        # Try notify-send (Linux)
        try:
            subprocess.run(['notify-send', 'Task Manager', message], capture_output=True, check=False)
            logger.debug("Notification sent via notify-send (Linux)")
        except Exception as e:
            logger.debug(f"notify-send not available: {e}")
        
        # Try osascript (macOS)
        try:
            subprocess.run(['osascript', '-e', f'display notification "{message}" with title "Task Manager"'], capture_output=True, check=False)
            logger.debug("Notification sent via osascript (macOS)")
        except Exception as e:
            logger.debug(f"osascript not available: {e}")
        
        # Try PowerShell (Windows)
        try:
            subprocess.run(['powershell', '-Command', f'New-Object -TypeName System.Windows.Forms.NotifyIcon -ArgumentList | % {{ $_.Icon = [System.Drawing.SystemIcons]::Information; $_.BalloonTipTitle = "Task Manager"; $_.BalloonTipText = "{message}"; $_.ShowBalloonTip(10000) }}'], capture_output=True, check=False)
            logger.debug("Notification sent via PowerShell (Windows)")
        except Exception as e:
            logger.debug(f"PowerShell not available: {e}")
    
    def start(self):
        """Start the reminder monitoring loop"""
        logger.info("Starting reminder system")
        self.running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        print("🔔 Reminder system started")
    
    def stop(self):
        """Stop the reminder monitoring loop"""
        logger.info("Stopping reminder system")
        self.running = False
    
    def _run(self):
        """Main loop to check for due reminders"""
        logger.debug("Reminder system loop started")
        while self.running:
            try:
                due_reminders = self.task_manager.get_due_reminders()
                if due_reminders:
                    logger.info(f"Found {len(due_reminders)} due reminders")
                for task, reminder in due_reminders:
                    self.notify(task, reminder)
            except Exception as e:
                logger.error(f"Reminder check error: {e}")
            time.sleep(self.check_interval)
    
    def set_reminder_for_task(self, task_id: str, minutes_before: int = 0, specific_time: datetime = None):
        """Set a reminder for a task"""
        logger.info(f"Setting reminder for task: {task_id}")
        
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.warning(f"Task not found for reminder: {task_id}")
            return None
        
        if specific_time:
            reminder_time = specific_time
            logger.debug(f"Using specific time: {reminder_time}")
        elif task.due_date:
            reminder_time = task.due_date - timedelta(minutes=minutes_before)
            logger.debug(f"Using due date minus {minutes_before} minutes: {reminder_time}")
        else:
            # Default to now + 30 minutes
            reminder_time = datetime.now() + timedelta(minutes=30)
            logger.debug(f"Using default time (now + 30min): {reminder_time}")
        
        reminder = self.task_manager.add_reminder(task_id, reminder_time)
        logger.info(f"Reminder set for task {task_id} at {reminder_time}")
        return reminder