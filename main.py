""" Main entry point - provides both CLI and API for OpenClaw """
from task_manager_package.task_manager import TaskManager, Priority
from scheduler import SchedulerConfig, AIScheduler
from reminder import ReminderSystem
from tools import TaskTools

import os
import sys
import json
import subprocess
from pathlib import Path

# Use absolute paths based on script location
SCRIPT_DIR = Path(__file__).parent

TASKS_FILE = Path(os.getenv('TASKS_FILE', SCRIPT_DIR / 'my_tasks.json'))
CONFIG_FILE = Path(os.getenv('CONFIG_FILE', SCRIPT_DIR / 'config.json'))

# Initialize components
task_manager = TaskManager(str(TASKS_FILE))
config = SchedulerConfig(str(CONFIG_FILE))
scheduler = AIScheduler(task_manager, config)
reminder_system = ReminderSystem(task_manager)
task_tools = TaskTools(task_manager, scheduler, reminder_system)

# Register OpenClaw Telegram callback if configured
OPENCLAW_BIN = os.getenv('OPENCLAW_BIN', '/home/sanchitingale339/.npm-global/bin/openclaw')
TELEGRAM_TARGET = os.getenv('OPENCLAW_TELEGRAM_TARGET', '')


def send_telegram_reminder(task, reminder):
    """Send reminder notification via OpenClaw Telegram"""
    if not TELEGRAM_TARGET:
        return

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
    except Exception as e:
        print(f"Failed to send Telegram reminder: {e}", file=sys.stderr)


if TELEGRAM_TARGET:
    reminder_system.add_callback(send_telegram_reminder)
    print(f"📱 OpenClaw Telegram reminders enabled for {TELEGRAM_TARGET}", file=sys.stderr)

# Start reminder system
reminder_system.start()


# ==================== RESPONSE HELPERS ====================

def success_response(data=None, message=None):
    """Build a standardized success response envelope."""
    response = {"ok": True}
    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
    return response


def error_response(code, message):
    """Build a standardized error response envelope."""
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message
        }
    }


# ==================== FLASK APP FACTORY ====================

def create_app():
    """Factory function to create the Flask app (for testing and programmatic start)."""
    from flask import Flask, request

    app = Flask(__name__)

    # Error handlers for JSON error responses
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(400, str(e.description))

    @app.errorhandler(404)
    def not_found(e):
        return error_response(404, "Resource not found")

    @app.errorhandler(500)
    def internal_error(e):
        return error_response(500, "Internal server error")

    @app.route('/api/tasks', methods=['POST'])
    def api_create_task():
        try:
            data = request.json
            result = task_tools.create_task(**data)
            # Determine if result is structured data or a message
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/tasks', methods=['GET'])
    def api_list_tasks():
        try:
            project = request.args.get('project')
            today = request.args.get('today', '').lower() == 'true'
            overdue = request.args.get('overdue', '').lower() == 'true'
            high_priority = request.args.get('high_priority', '').lower() == 'true'
            limit = request.args.get('limit')
            offset = request.args.get('offset', '0')

            # Parse limit and offset
            limit_int = int(limit) if limit and limit.isdigit() else None
            offset_int = int(offset) if offset.isdigit() else 0

            result = task_tools.list_tasks(
                project=project,
                today=today,
                overdue=overdue,
                high_priority=high_priority,
                limit=limit_int,
                offset=offset_int
            )
            # list_tasks returns a structured list, so pass as data
            return success_response(data=result)
        except Exception as e:
            return error_response(500, str(e))

    @app.route('/api/tasks/batch', methods=['POST'])
    def api_batch_create():
        try:
            data = request.json
            result = task_tools.batch_create_tasks(
                task_list=data.get('tasks', []),
                project=data.get('project', 'Inbox'),
                due_date=data.get('due_date')
            )
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/tasks/<task_id>/complete', methods=['POST'])
    def api_complete_task(task_id):
        try:
            result = task_tools.complete_task(task_id)
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/tasks/<task_id>/reminder', methods=['POST'])
    def api_set_reminder(task_id):
        try:
            data = request.json
            result = task_tools.set_reminder(
                task_id=task_id,
                minutes_before=data.get('minutes_before', 30),
                specific_time=data.get('specific_time')
            )
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/schedule', methods=['GET'])
    def api_get_schedule():
        try:
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
            return success_response(data={"schedule": schedule})
        except Exception as e:
            return error_response(500, str(e))

    @app.route('/api/schedule/suggestions', methods=['GET'])
    def api_schedule_suggestions():
        try:
            result = task_tools.get_schedule_suggestions()
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(500, str(e))

    @app.route('/api/routine', methods=['POST'])
    def api_update_routine():
        try:
            data = request.json
            result = task_tools.update_routine(**data)
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/holidays', methods=['POST'])
    def api_add_holiday():
        try:
            data = request.json
            result = task_tools.add_holiday(data.get('date'), data.get('name', ''))
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/comp-off', methods=['POST'])
    def api_add_comp_off():
        try:
            data = request.json
            result = task_tools.add_comp_off(data.get('date'))
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(400, str(e))

    @app.route('/api/projects', methods=['GET'])
    def api_list_projects():
        try:
            result = task_tools.list_projects()
            if isinstance(result, dict):
                return success_response(data=result)
            return success_response(message=result)
        except Exception as e:
            return error_response(500, str(e))

    @app.route('/api/tools', methods=['GET'])
    def api_get_tools():
        try:
            result = task_tools.get_all_tools()
            return success_response(data=result)
        except Exception as e:
            return error_response(500, str(e))

    return app


# ==================== STDIO MODE (OpenClaw Local Tools) ====================

def run_stdio_mode():
    """Run in stdio mode for OpenClaw local tool execution"""
    try:
        while True:
            # Read JSON-RPC request from stdin
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line.strip())
            except json.JSONDecodeError as e:
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
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {tool_name}"
                            }
                        }
                except Exception as e:
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
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }

            else:
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
        pass
    except Exception as e:
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
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "serve":
            # Get port from CLI arg or environment variable (CLI arg takes precedence)
            port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.getenv('FLASK_PORT', 5000))
            
            # Get host from environment variable (default to 0.0.0.0)
            host = os.getenv('FLASK_HOST', '0.0.0.0')
            
            # Get debug mode from environment variable
            debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
            
            app = create_app()
            print(f"🚀 Starting Task Manager API on {host}:{port}")
            app.run(host=host, port=port, debug=debug)

        elif command == "create":
            title = " ".join(sys.argv[2:])
            print(task_tools.create_task(title))

        elif command == "list":
            print(task_tools.list_tasks())

        elif command == "today":
            print(task_tools.list_tasks(today=True))

        elif command == "schedule":
            print(task_tools.get_schedule_suggestions())

        elif command == "stdio":
            # Start stdio mode for OpenClaw local tools
            print("🔌 Starting stdio mode for OpenClaw integration...", file=sys.stderr)
            run_stdio_mode()

        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        # Interactive mode
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
   FLASK_PORT=<port>     # Default server port (default: 5000)
   FLASK_HOST=<host>     # Server host (default: 0.0.0.0)
   FLASK_DEBUG=<true>    # Enable debug mode

 API Endpoints:
   POST   /api/tasks                 - Create task
   GET    /api/tasks                 - List tasks
   POST   /api/tasks/batch           - Batch create tasks
   POST   /api/tasks/<id>/complete   - Complete task
   POST   /api/tasks/<id>/reminder   - Set reminder
   GET    /api/schedule              - Get schedule
   GET    /api/schedule/suggestions  - Get AI suggestions
   POST   /api/routine               - Update routine
   POST   /api/holidays              - Add holiday
   POST   /api/comp-off              - Add comp-off
   
 Response Format:
   Success: {"ok": true, "data": ...} or {"ok": true, "message": "..."}
   Error:   {"ok": false, "error": {"code": <code>, "message": "..."}}
""")


def print_usage():
    """Print command usage information"""
    print("Usage:")
    print("  python main.py serve [port]       # Start API server (port defaults to 5000 or FLASK_PORT env)")
    print("  python main.py create <title>     # Create task")
    print("  python main.py list               # List all tasks")
    print("  python main.py today              # List today's tasks")
    print("  python main.py schedule           # Get AI schedule suggestions")
    print("  python main.py stdio              # Start stdio mode for OpenClaw")


if __name__ == "__main__":
    main()