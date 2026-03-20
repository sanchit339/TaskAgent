"""
Unlimited reminder system - No more 5 reminder limit!
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, List
import os
import subprocess


class ReminderSystem:
    def __init__(self, task_manager, check_interval: int = 30):
        self.task_manager = task_manager
        self.check_interval = check_interval
        self.running = False
        self.callbacks: List[Callable] = []

    def add_callback(self, callback: Callable):
        """Add a callback function to be called when reminder triggers"""
        self.callbacks.append(callback)

    def notify(self, task, reminder):
        """Send notification for a reminder"""
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
                callback(task, reminder)
            except Exception as e:
                print(f"Callback error: {e}")

        # Mark as notified
        self.task_manager.mark_reminder_notified(task.id, reminder.id)

    def _send_notification(self, message: str):
        """Send system notification"""
        try:
            # Try notify-send (Linux)
            subprocess.run(['notify-send', 'Task Manager', message],
                         capture_output=True, check=False)
        except:
            pass

        try:
            # Try osascript (macOS)
            subprocess.run(['osascript', '-e', f'display notification "{message}" with title "Task Manager"'],
                         capture_output=True, check=False)
        except:
            pass

        try:
            # Try PowerShell (Windows)
            subprocess.run(['powershell', '-Command',
                          f'New-Object -TypeName System.Windows.Forms.NotifyIcon -ArgumentList | % {{ $_.Icon = [System.Drawing.SystemIcons]::Information; $_.BalloonTipTitle = "Task Manager"; $_.BalloonTipText = "{message}"; $_.ShowBalloonTip(10000) }}'],
                         capture_output=True, check=False)
        except:
            pass

    def start(self):
        """Start the reminder monitoring loop"""
        self.running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        print("🔔 Reminder system started")

    def stop(self):
        """Stop the reminder monitoring loop"""
        self.running = False

    def _run(self):
        """Main loop to check for due reminders"""
        while self.running:
            try:
                due_reminders = self.task_manager.get_due_reminders()
                for task, reminder in due_reminders:
                    self.notify(task, reminder)
            except Exception as e:
                print(f"Reminder check error: {e}")

            time.sleep(self.check_interval)

    def set_reminder_for_task(self, task_id: str, minutes_before: int = 0, specific_time: datetime = None):
        """Set a reminder for a task"""
        task = self.task_manager.get_task(task_id)
        if not task:
            return None

        if specific_time:
            reminder_time = specific_time
        elif task.due_date:
            reminder_time = task.due_date - timedelta(minutes=minutes_before)
        else:
            # Default to now + 30 minutes
            reminder_time = datetime.now() + timedelta(minutes=30)

        return self.task_manager.add_reminder(task_id, reminder_time)
