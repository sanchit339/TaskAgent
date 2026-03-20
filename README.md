# Task Manager - OpenClaw Integration

A fully-featured Todoist clone with unlimited reminders and AI-powered scheduling, designed to work seamlessly with OpenClaw as a local tool.

## Features

- ✅ Unlimited reminders (no 5 reminder limit like Todoist)
- ✅ AI-powered scheduling based on your routine
- ✅ Holiday and comp-off awareness
- ✅ Recurring tasks (daily, weekly, monthly, weekdays)
- ✅ Priority levels (LOW, MEDIUM, HIGH, URGENT)
- ✅ Projects and labels
- ✅ Batch operations
- ✅ JSON persistence
- ✅ Flask REST API
- ✅ **Stdio mode for OpenClaw local tool execution**

## Quick Start

### Option 1: Stdio Mode (Recommended for OpenClaw)

OpenClaw will directly execute the task manager and communicate via stdin/stdout:

```bash
python3 main.py stdio
```

The tool expects JSON-RPC 2.0 formatted requests on stdin and outputs responses on stdout.

#### Example Stdio Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Review Q1 report",
      "project": "Work",
      "priority": "HIGH",
      "due_date": "2024-03-15"
    }
  }
}
```

#### Example Stdio Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": "✅ Task created: Review Q1 report (ID: abc123...)"
}
```

#### Tool Discovery

OpenClaw can fetch available tools:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "create_task",
        "description": "Create a new task with optional due date, priority, and project",
        "parameters": { ... }
      },
      ...
    ]
  }
}
```

### Option 2: API Mode

Start the Flask API server:

```bash
python3 main.py serve 5000
```

Then OpenClaw can make HTTP requests to `http://localhost:5000`.

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tools` | List all available tools |
| GET | `/api/tasks` | List tasks with filters |
| POST | `/api/tasks` | Create a task |
| POST | `/api/tasks/batch` | Batch create tasks |
| POST | `/api/tasks/<id>/complete` | Complete a task |
| POST | `/api/tasks/<id>/reminder` | Set a reminder |
| GET | `/api/schedule` | Get today's schedule |
| GET | `/api/schedule/suggestions` | Get AI schedule suggestions |
| POST | `/api/routine` | Update routine settings |
| POST | `/api/holidays` | Add a holiday |
| POST | `/api/comp-off` | Add a comp-off day |
| GET | `/api/projects` | List all projects |

## Available Tools (16 Total)

### Task Management
- `create_task` - Create a new task with full options
- `create_urgent_task` - Create high-priority urgent task
- `add_to_project` - Add task to specific project
- `create_recurring_task` - Create recurring task (daily/weekly/monthly/weekdays)
- `batch_create_tasks` - Create multiple tasks at once
- `complete_task` - Mark task as completed (by ID or title)
- `delete_task` - Delete a task
- `list_tasks` - List tasks with optional filters
- `get_task_details` - Get detailed task information

### Scheduling
- `get_schedule` - Get schedule for a specific day
- `get_schedule_suggestions` - Get AI-powered schedule suggestions
- `update_routine` - Update work hours, lunch breaks, work days
- `add_holiday` - Add holiday (scheduler avoids these)
- `add_comp_off` - Add compensatory off day (treated as work day)

### Reminders
- `set_reminder` - Set reminder (unlimited!) with minutes_before or specific_time

### Utilities
- `list_projects` - List all available projects

## Configuration

Edit `config.json` to customize:

```json
{
  "routine": {
    "work_start": "09:00",
    "work_end": "18:00",
    "work_days": [0, 1, 2, 3, 4],  // Monday=0, Sunday=6
    "lunch_start": "13:00",
    "lunch_end": "14:00",
    "sleep_start": "23:00",
    "sleep_end": "07:00"
  },
  "holidays": ["2024-01-26", "2024-08-15"],
  "comp_offs": [],
  "default_task_duration": 30
}
```

## CLI Commands (Manual Testing)

```bash
# Start API server
python3 main.py serve 5000

# Start stdio mode for OpenClaw
python3 main.py stdio

# Quick task creation
python3 main.py create "Buy groceries"

# List tasks
python3 main.py list

# Show today's tasks
python3 main.py today

# Get schedule suggestions
python3 main.py schedule
```

## Data Storage

- Tasks: `my_tasks.json`
- Configuration: `config.json`

Both use JSON format for easy inspection and backup.

## Setting Up OpenClaw

In your OpenClaw configuration, add a tool with:

```yaml
  task_manager:
    type: local
    command: python3
    args: ["/home/sanchitingale339/task_manager/main.py", "stdio"]
```

The exact configuration depends on your OpenClaw setup. Consult OpenClaw's documentation for how to register a local tool that uses stdin/stdout JSON-RPC.

## Testing Stdio Mode Manually

You can test the stdio mode by piping JSON:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_tasks","arguments":{}}}' | python3 main.py stdio
```

## Notes

- All dates should be in ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`
- Times use 24-hour format: `HH:MM`
- Priority values: `LOW`, `MEDIUM`, `HIGH`, `URGENT`
- Recurrence patterns: `DAILY`, `WEEKLY`, `MONTHLY`, `WEEKDAYS`
- The reminder system runs in the background and checks every 30 seconds

## Dependencies

```bash
pip install flask apscheduler pytz colorama
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/task-manager.git
   ```
2. Navigate to the project directory:
   ```bash
   cd task-manager
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Usage

Start the API server:
```bash
python main.py serve
```

Access the API endpoints:
- Create Task: `POST /api/tasks`
- List Tasks: `GET /api/tasks`
- Complete Task: `POST /api/tasks/<task_id>/complete`
- Set Reminder: `POST /api/tasks/<task_id>/reminder`

## License

This project is licensed under the MIT License. See the LICENSE file for details.
