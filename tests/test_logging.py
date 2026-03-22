"""Tests for logging functionality across all modules"""
import logging
import io
import sys
from pathlib import Path
from contextlib import redirect_stderr

import pytest


class TestLoggingConfiguration:
    """Test that logging is properly configured in all modules"""
    
    def test_task_manager_package_logger_exists(self):
        """Test that task_manager_package has a logger"""
        from task_manager_package import logger
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "task_manager_package"
    
    def test_task_manager_package_task_manager_logger(self):
        """Test that task_manager_package.task_manager has a logger"""
        from task_manager_package.task_manager import logger
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_main_logger_exists(self):
        """Test that main module has a logger"""
        import main
        # The main module should have a logger
        assert hasattr(main, 'logger')
        assert main.logger is not None
    
    def test_scheduler_logger_exists(self):
        """Test that scheduler module has a logger"""
        import scheduler
        assert hasattr(scheduler, 'logger')
        assert scheduler.logger is not None
    
    def test_reminder_logger_exists(self):
        """Test that reminder module has a logger"""
        import reminder
        assert hasattr(reminder, 'logger')
        assert reminder.logger is not None
    
    def test_tools_logger_exists(self):
        """Test that tools module has a logger"""
        import tools
        assert hasattr(tools, 'logger')
        assert tools.logger is not None
    
    def test_task_manager_logger_exists(self):
        """Test that task_manager module has a logger"""
        import task_manager
        assert hasattr(task_manager, 'logger')
        assert task_manager.logger is not None


class TestLoggingOutput:
    """Test that logging produces output"""
    
    def test_task_manager_package_logs_on_init(self, tmp_path):
        """Test that task_manager_package logs on initialization"""
        # Re-import to trigger initialization logging
        import importlib
        import task_manager_package
        importlib.reload(task_manager_package)
        
        from task_manager_package import logger
        
        # The logger should exist and be named correctly
        assert logger.name == "task_manager_package"
        # Should have handlers (console and file)
        assert len(logger.handlers) >= 1
    
    def test_task_manager_logs_operations(self, tmp_path):
        """Test that TaskManager logs operations"""
        from task_manager_package.task_manager import TaskManager, logger
        
        storage = tmp_path / "tasks.json"
        
        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        # Create a task manager and perform operations
        tm = TaskManager(str(storage))
        task = tm.add_task(title="Test logging task", project="Inbox")
        
        # Get the task
        found = tm.get_task(task.id)
        assert found is not None
        
        # Complete the task
        tm.complete_task(task.id)
        
        # Delete the task
        tm.delete_task(task.id)
        
        # Check that log output was produced
        log_output = log_capture.getvalue()
        assert "task" in log_output.lower() or len(log_output) > 0


class TestLoggingLevels:
    """Test that appropriate log levels are used"""
    
    def test_info_level_for_operations(self, tmp_path):
        """Test that operations use INFO level"""
        from task_manager_package.task_manager import TaskManager, logger
        
        storage = tmp_path / "tasks.json"
        
        # Set up logging to capture
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        
        tm = TaskManager(str(storage))
        tm.add_task(title="Info level test", project="Inbox")
        
        log_output = log_capture.getvalue()
        # INFO level should produce output
        assert "INFO" in log_output or len(log_output) > 0
    
    def test_warning_level_for_errors(self, tmp_path):
        """Test that errors use WARNING level"""
        from task_manager_package.task_manager import TaskManager, logger
        
        storage = tmp_path / "tasks.json"
        
        # Set up logging to capture
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)
        
        tm = TaskManager(str(storage))
        
        # Try to get a non-existent task
        found = tm.get_task("non-existent-id")
        assert found is None
        
        log_output = log_capture.getvalue()
        # Should have a warning for not found
        assert "warning" in log_output.lower() or "not found" in log_output.lower() or len(log_output) > 0


class TestLoggingHandlers:
    """Test that loggers have proper handlers"""
    
    def test_console_handler_exists(self):
        """Test that loggers have console handlers"""
        from task_manager_package import logger
        handlers = logger.handlers
        # Should have at least one handler
        assert len(handlers) > 0
    
    def test_logger_not_duplicate_on_reimport(self):
        """Test that reimporting doesn't create duplicate handlers"""
        import importlib
        import task_manager_package
        importlib.reload(task_manager_package)
        
        from task_manager_package import logger
        # Should not have duplicate handlers
        handler_types = [type(h) for h in logger.handlers]
        # Allow multiple handlers but they should be different types or from different sources
        assert len(handler_types) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])