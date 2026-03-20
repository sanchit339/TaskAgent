"""
Main entry point - provides both CLI and API for OpenClaw
"""

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


# ==================== CLI INTERFACE ====================

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


def main():
    """Main function with CLI"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "serve":
            from flask import Flask, request, jsonify
            app = Flask(__name__)

            @app.route('/api/tasks', methods=['POST'])
            def api_create_task():
                data = request.json
                result = task_tools.create_task(**data)
                return jsonify({"result": result})

            @app.route('/api/tasks', methods=['GET'])
            def api_list_tasks():
                project = request.args.get('project')
                today = request.args.get('today', '').lower() == 'true'
                overdue = request.args.get('overdue', '').lower() == 'true'
                high_priority = request.args.get('high_priority', '').lower() == 'true'
                result = task_tools.list_tasks(
                    project=project,
                    today=today,
                    overdue=overdue,
                    high_priority=high_priority
                )
                return jsonify({"result": result})

            @app.route('/api/tasks/batch', methods=['POST'])
            def api_batch_create():
                data = request.json
                result = task_tools.batch_create_tasks(
                    task_list=data.get('tasks', []),
                    project=data.get('project', 'Inbox'),
                    due_date=data.get('due_date')
                )
                return jsonify({"result": result})

            @app.route('/api/tasks/<task_id>/complete', methods=['POST'])
            def api_complete_task(task_id):
                result = task_tools.complete_task(task_id)
                return jsonify({"result": result})

            @app.route('/api/tasks/<task_id>/reminder', methods=['POST'])
            def api_set_reminder(task_id):
                data = request.json
                result = task_tools.set_reminder(
                    task_id=task_id,
                    minutes_before=data.get('minutes_before', 30),
                    specific_time=data.get('specific_time')
                )
                return jsonify({"result": result})

            @app.route('/api/schedule', methods=['GET'])
            def api_get_schedule():
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
                return jsonify({"schedule": schedule})

            @app.route('/api/schedule/suggestions', methods=['GET'])
            def api_schedule_suggestions():
                result = task_tools.get_schedule_suggestions()
                return jsonify({"result": result})

            @app.route('/api/routine', methods=['POST'])
            def api_update_routine():
                data = request.json
                result = task_tools.update_routine(**data)
                return jsonify({"result": result})

            @app.route('/api/holidays', methods=['POST'])
            def api_add_holiday():
                data = request.json
                result = task_tools.add_holiday(data.get('date'), data.get('name', ''))
                return jsonify({"result": result})

            @app.route('/api/comp-off', methods=['POST'])
            def api_add_comp_off():
                data = request.json
                result = task_tools.add_comp_off(data.get('date'))
                return jsonify({"result": result})

            @app.route('/api/projects', methods=['GET'])
            def api_list_projects():
                result = task_tools.list_projects()
                return jsonify({"result": result})

            @app.route('/api/tools', methods=['GET'])
            def api_get_tools():
                return jsonify(task_tools.get_all_tools())

            port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
            print(f"🚀 Starting Task Manager API on port {port}")
            app.run(host='0.0.0.0', port=port)

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
            print("Usage:")
            print("  python main.py serve [port]    # Start API server")
            print("  python main.py create <title>  # Create task")
            print("  python main.py list            # List all tasks")
            print("  python main.py today           # List today's tasks")
            print("  python main.py schedule        # Get schedule suggestions")
            print("  python main.py stdio           # Start stdio mode for OpenClaw")
    else:
        # Interactive mode
        print("""
🤖 Task Manager - OpenClaw Integration Ready!

Commands:
  python main.py serve         # Start API server (port 5000)
  python main.py create <task> # Create a new task
  python main.py list          # List all tasks
  python main.py today         # List today's tasks
  python main.py schedule      # Get AI schedule suggestions
  python main.py stdio         # Start stdio mode for OpenClaw local tools

API Endpoints:
  POST /api/tasks          - Create task
  GET /api/tasks           - List tasks
  POST /api/tasks/batch    - Batch create tasks
  POST /api/tasks/<id>/complete - Complete task
  POST /api/tasks/<id>/reminder - Set reminder
  GET /api/schedule        - Get schedule
  GET /api/schedule/suggestions - Get AI suggestions
  POST /api/routine        - Update routine
  POST /api/holidays       - Add holiday
  POST /api/comp-off       - Add comp-off
        """)
