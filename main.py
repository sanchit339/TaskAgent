""" Main entry point - provides both CLI and API for OpenClaw """
from src.logging_utils import setup_logger
from src.api_utils import success_response, error_response

logger = setup_logger("main")

# Now import after logging is set up
from src import TaskManager, Priority
from src.scheduler import SchedulerConfig, AIScheduler
from src.reminder import ReminderSystem
from src.tools import TaskTools
import os
import sys
import json
import subprocess
from pathlib import Path

# Use absolute paths based on script location
SCRIPT_DIR = Path(__file__).parent
TASKS_FILE = Path(os.getenv('TASKS_FILE', SCRIPT_DIR / 'my_tasks.json'))
CONFIG_FILE = Path(os.getenv('CONFIG_FILE', SCRIPT_DIR / 'config.json'))

logger.info(f"Initializing Task Manager - Tasks file: {TASKS_FILE}, Config: {CONFIG_FILE}")

# Initialize components
task_manager = TaskManager(str(TASKS_FILE))
config = SchedulerConfig(str(CONFIG_FILE))
scheduler = AIScheduler(task_manager, config)
reminder_system = ReminderSystem(task_manager)
task_tools = TaskTools(task_manager, scheduler, reminder_system)

logger.info("All components initialized successfully")

# Register OpenClaw Telegram callback if configured
OPENCLAW_BIN = os.getenv('OPENCLAW_BIN')
TELEGRAM_TARGET = os.getenv('OPENCLAW_TELEGRAM_TARGET', '')

def send_telegram_reminder(task, reminder):
    """Send reminder notification via OpenClaw Telegram"""
    if not TELEGRAM_TARGET:
        return
    
    logger.info(f"Sending Telegram reminder for task: {task.id}")
    
    message = f"🔔 Reminder: {task.title}"
    if task.due_date:
        message += f"\nDue: {task.due_date.strftime('%Y-%m-%d %H:%M')}"
    if task.project != "Inbox":
        message += f"\nProject: {task.project}"
    
    try:
        subprocess.run(
            [OPENCLAW_BIN, "message", "send", "--target", TELEGRAM_TARGET, "--message", message],
            timeout=10,
            capture_output=True
        )
        logger.debug(f"Telegram reminder sent successfully for task {task.id}")
    except Exception as e:
        logger.error(f"Failed to send Telegram reminder: {e}")
        print(f"Failed to send Telegram reminder: {e}", file=sys.stderr)

if TELEGRAM_TARGET:
    reminder_system.add_callback(send_telegram_reminder)
    print(f"📱 OpenClaw Telegram reminders enabled for {TELEGRAM_TARGET}", file=sys.stderr)
    logger.info(f"Telegram reminders enabled for target: {TELEGRAM_TARGET}")

# Start reminder system
reminder_system.start()

# ==================== FLASK APP FACTORY ====================

def create_app():
    """Factory function to create the Flask app (for testing and programmatic start)."""
    from flask import Flask, request
    
    logger.info("Creating Flask application")
    
    app = Flask(__name__)
    
    # Error handlers for JSON error responses
    @app.errorhandler(400)
    def bad_request(e):
        logger.warning(f"Bad request: {e.description}")
        return error_response(400, str(e.description))
    
    @app.errorhandler(404)
    def not_found(e):
        logger.warning(f"Resource not found: {e}")
        return error_response(404, "Resource not found")
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return error_response(500, "Internal server error")
    
    @app.route('/api/tasks', methods=['POST'])
    def api_create_task():
        try:
            logger.debug("API: Creating task")
            data = request.json
            result = task_tools.create_task(**data)
            # Determine if result is structured data or a message
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in create_task: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/tasks', methods=['GET'])
    def api_list_tasks():
        try:
            logger.debug("API: Listing tasks")
            project = request.args.get('project')
            today = request.args.get('today', '').lower() == 'true'
            overdue = request.args.get('overdue', '').lower() == 'true'
            high_priority = request.args.get('high_priority', '').lower() == 'true'
            limit = request.args.get('limit')
            offset = request.args.get('offset', '0')
            
            # Parse limit and offset
            limit_int = int(limit) if limit and limit.isdigit() else None
            offset_int = int(offset) if offset and offset.isdigit() else 0
            
            result = task_tools.list_tasks(
                project=project,
                today=today,
                overdue=overdue,
                high_priority=high_priority,
                limit=limit_int,
                offset=offset_int
            )
            # list_tasks returns a structured list, so pass as data
            return success_response(data=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in list_tasks: {e}")
            return error_response(500, str(e))
    
    @app.route('/api/tasks/batch', methods=['POST'])
    def api_batch_create():
        try:
            logger.debug("API: Batch creating tasks")
            data = request.json
            result = task_tools.batch_create_tasks(
                task_list=data.get('tasks', []),
                project=data.get('project', 'Inbox'),
                due_date=data.get('due_date')
            )
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in batch_create: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/tasks/<task_id>/complete', methods=['POST'])
    def api_complete_task(task_id):
        try:
            logger.debug(f"API: Completing task {task_id}")
            result = task_tools.complete_task(task_id)
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in complete_task: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/tasks/<task_id>/reminder', methods=['POST'])
    def api_set_reminder(task_id):
        try:
            logger.debug(f"API: Setting reminder for task {task_id}")
            data = request.json
            result = task_tools.set_reminder(
                task_id=task_id,
                minutes_before=data.get('minutes_before', 30),
                specific_time=data.get('specific_time')
            )
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in set_reminder: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/schedule', methods=['GET'])
    def api_get_schedule():
        try:
            logger.debug("API: Getting schedule")
            date = request.args.get('date')
            result = task_manager.get_tasks(due_today=True, completed=False)
            schedule = []
            for task in result:
                if task.scheduled_time:
                    schedule.append({
                        "time": task.scheduled_time.strftime("%H:%M"),
                        "task": task.title,
                        "duration": task.estimated_duration,
                        "priority": task.priority.name,
                        "project": task.project
                    })
            return success_response(data={"schedule": schedule}, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in get_schedule: {e}")
            return error_response(500, str(e))
    
    @app.route('/api/schedule/suggestions', methods=['GET'])
    def api_schedule_suggestions():
        try:
            logger.debug("API: Getting schedule suggestions")
            result = task_tools.get_schedule_suggestions()
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in schedule_suggestions: {e}")
            return error_response(500, str(e))
    
    @app.route('/api/routine', methods=['POST'])
    def api_update_routine():
        try:
            logger.debug("API: Updating routine")
            data = request.json
            result = task_tools.update_routine(**data)
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in update_routine: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/holidays', methods=['POST'])
    def api_add_holiday():
        try:
            logger.debug("API: Adding holiday")
            data = request.json
            result = task_tools.add_holiday(data.get('date'), data.get('name', ''))
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in add_holiday: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/comp-off', methods=['POST'])
    def api_add_comp_off():
        try:
            logger.debug("API: Adding comp-off")
            data = request.json
            result = task_tools.add_comp_off(data.get('date'))
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in add_comp_off: {e}")
            return error_response(400, str(e))
    
    @app.route('/api/projects', methods=['GET'])
    def api_list_projects():
        try:
            logger.debug("API: Listing projects")
            result = task_tools.list_projects()
            if isinstance(result, dict):
                return success_response(data=result, use_legacy_format=True)
            return success_response(message=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in list_projects: {e}")
            return error_response(500, str(e))
    
    @app.route('/api/tools', methods=['GET'])
    def api_get_tools():
        try:
            logger.debug("API: Getting tools")
            result = task_tools.get_all_tools()
            return success_response(data=result, use_legacy_format=True)
        except Exception as e:
            logger.error(f"API error in get_tools: {e}")
            return error_response(500, str(e))
    
    logger.info("Flask application created successfully")
    return app

# ==================== STDIO MODE (OpenClaw Local Tools) ====================

def run_stdio_mode():
    """Run in stdio mode for OpenClaw local tool execution"""
    logger.info("Starting stdio mode for OpenClaw integration")
    try:
        while True:
            # Read JSON-RPC request from stdin
            line = sys.stdin.readline(65536)
            if not line:
                break
            
            try:
                request = json.loads(line.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                continue
            
            # Extract request parameters
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Handle tool calls
            if method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                logger.debug(f"STDIO: Calling tool {tool_name}")
                try:
                    # Call the appropriate tool method
                    if hasattr(task_tools, tool_name):
                        tool_method = getattr(task_tools, tool_name)
                        result = tool_method(**tool_args)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        }
                    else:
                        logger.warning(f"STDIO: Method not found: {tool_name}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {tool_name}"
                            }
                        }
                except Exception as e:
                    logger.error(f"STDIO error in {tool_name}: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
            elif method == "tools/list":
                # Return list of available tools
                logger.debug("STDIO: Listing tools")
                try:
                    tools = task_tools.get_all_tools()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": list(tools.values())
                        }
                    }
                except Exception as e:
                    logger.error(f"STDIO error in tools/list: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
            else:
                logger.warning(f"STDIO: Method not found: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            # Send response to stdout
            print(json.dumps(response), flush=True)
    
    except KeyboardInterrupt:
        logger.info("STDIO mode interrupted")
        pass
    except Exception as e:
        logger.error(f"STDIO fatal error: {e}")
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Fatal error: {str(e)}"
            }
        }), flush=True)

# Duplicate create_app removed; the primary factory is defined above.

def main():
    """Main function with CLI"""
    logger.info("Starting main function")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "serve":
            # Get port from CLI arg or environment variable (CLI arg takes precedence)
            port_str = sys.argv[2] if len(sys.argv) > 2 else os.getenv('FLASK_PORT', '5000')
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError(f"Port {port} is out of valid range (1-65535)")
            except ValueError as e:
                logger.error(f"Invalid port value: {port_str}. {e}")
                print(f"Error: Invalid port value '{port_str}'. Port must be between 1 and 65535.")
                sys.exit(1)
        
            # Get host from environment variable (default to 0.0.0.0)
            host = os.getenv('FLASK_HOST', '0.0.0.0')
            
            # Get debug mode from environment variable
            debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
            
            logger.info(f"Starting Flask server on {host}:{port}, debug={debug}")
            app = create_app()
            print(f"🚀 Starting Task Manager API on {host}:{port}")
            app.run(host=host, port=port, debug=debug)
        
        elif command == "create":
            title = " ".join(sys.argv[2:])
            logger.info(f"Creating task via CLI: {title}")
            print(task_tools.create_task(title))
        
        elif command == "list":
            logger.info("Listing tasks via CLI")
            print(task_tools.list_tasks())
        
        elif command == "today":
            logger.info("Listing today's tasks via CLI")
            print(task_tools.list_tasks(today=True))
        
        elif command == "schedule":
            logger.info("Getting schedule suggestions via CLI")
            print(task_tools.get_schedule_suggestions())
        
        elif command == "stdio":
            # Start stdio mode for OpenClaw local tools
            print("🔌 Starting stdio mode for OpenClaw integration...", file=sys.stderr)
            run_stdio_mode()
        
        else:
            logger.warning(f"Unknown command: {command}")
            print(f"Unknown command: {command}")
            print_usage()
    
    else:
        # Interactive mode
        logger.info("Showing interactive help")
        print("""
 🤖 Task Manager - OpenClaw Integration Ready!

 Commands:
   python main.py serve              # Start API server (default port 5000)
   python main.py serve <port>       # Start API server on custom port
   python main.py create <task>      # Create a new task
   python main.py list               # List all tasks
   python main.py today              # List today's tasks
   python main.py schedule           # Get AI schedule suggestions
   python main.py stdio              # Start stdio mode for OpenClaw local tools

 Environment Variables:
   FLASK_PORT=<port>                 # Default server port (default: 5000)
   FLASK_HOST=<host>                 # Server host (default: 0.0.0.0)
   FLASK_DEBUG=<true>                # Enable debug mode

 API Endpoints:
   POST   /api/tasks                 # Create task
   GET    /api/tasks                 # List tasks
   POST   /api/tasks/batch           # Batch create tasks
   POST   /api/tasks/<id>/complete   # Complete task
   POST   /api/tasks/<id>/reminder   # Set reminder
   GET    /api/schedule              # Get schedule
   GET    /api/schedule/suggestions  # Get AI suggestions
   POST   /api/routine               # Update routine
   POST   /api/holidays              # Add holiday
   POST   /api/comp-off              # Add comp-off

 Response Format:
   Success: {"ok": true, "data": ...} or {"ok": true, "message": "..."}
   Error:   {"ok": false, "error": {"code": <code>, "message": "..."}}
 """)

def print_usage():
    """Print command usage information"""
    print("Usage:")
    print("  python main.py serve [port]   # Start API server (port defaults to 5000 or FLASK_PORT env)")
    print("  python main.py create <title> # Create task")
    print("  python main.py list           # List all tasks")
    print("  python main.py today          # List today's tasks")
    print("  python main.py schedule       # Get AI schedule suggestions")
    print("  python main.py stdio          # Start stdio mode for OpenClaw")

if __name__ == "__main__":
    main()