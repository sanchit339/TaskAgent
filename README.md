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

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sanchit339/TaskAgent.git
   ```
2. Navigate to the project directory:
   ```bash
   cd TaskAgent
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
