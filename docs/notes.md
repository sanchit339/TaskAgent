# Task Manager (TaskAgent) — Project Notes

> Comprehensive documentation covering architecture, the development journey, issues encountered, and lessons learned.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [The Journey: Issues & Fixes](#the-journey-issues--fixes)
4. [Reminder System Deep Dive](#reminder-system-deep-dive)
5. [OpenClaw Integration](#openclaw-integration)
6. [Timezone Handling](#timezone-handling)
7. [Current State](#current-state)
8. [Lessons Learned](#lessons-learned)

---

## Project Overview

TaskAgent is a self-hosted task management system designed as an alternative to Todoist, built specifically for integration with [OpenClaw](https://openclaw.ai) — an AI agent platform. It provides:

- **Unlimited reminders** (Todoist's free tier caps at 5)
- **AI-powered scheduling** based on work routine, holidays, and comp-offs
- **Dual interfaces**: Flask REST API + JSON-RPC stdio mode for OpenClaw tool calls
- **System cron-based reminders** for reliability (no dependency on external services)

The project runs on a GCP `e2-standard-2` instance in `asia-south1`, Ubuntu 22.04, with the instance set to auto-delete on April 1, 2026.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        OpenClaw Agent                            │
│                                                                  │
│   User says: "remind me at 6pm to take socks"                   │
│                    │                                             │
│                    ▼                                             │
│   Agent (LLM) parses intent → extracts time, message, type      │
│                    │                                             │
│         ┌──────────┴──────────┐                                  │
│         ▼                     ▼                                  │
│   ┌──────────┐        ┌──────────────┐                          │
│   │ API Mode │        │  Stdio Mode  │                          │
│   │ (Flask)  │        │ (JSON-RPC)   │                          │
│   └────┬─────┘        └──────┬───────┘                          │
│        │                     │                                   │
│        └──────────┬──────────┘                                  │
│                   ▼                                              │
│   ┌─────────────────────────────────────┐                       │
│   │         TaskManager Core            │                       │
│   │  - Task CRUD (task_manager.py)      │                       │
│   │  - AI Scheduling (scheduler.py)     │                       │
│   │  - Tool Definitions (tools.py)      │                       │
│   │  - JSON persistence (my_tasks.json) │                       │
│   └─────────────────────────────────────┘                       │
│                   │                                              │
│                   ▼                                              │
│   ┌─────────────────────────────────────┐                       │
│   │        Reminder System              │                       │
│   │  System cron → scripts/             │                       │
│   │  reminder-runner.py → Telegram      │                       │
│   └─────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — Flask API + stdio JSON-RPC mode |
| `src/task_manager.py` | Core Task/Reminder dataclasses, TaskManager class |
| `src/tools.py` | OpenClaw tool definitions (TaskTools class) |
| `src/scheduler.py` | AI scheduling (AIScheduler, SchedulerConfig) |
| `src/constants.py` | Centralized defaults (priorities, durations) |
| `src/api_utils.py` | Response formatting helpers |
| `src/logging_utils.py` | Logging setup |
| `config.json` | Work routine, holidays, comp-offs |
| `openclaw_skill.yaml` | OpenClaw skill registration (tool schemas) |

---

## The Journey: Issues & Fixes

### Phase 1: Reminder System Hallucination Crisis

**The Problem:**
OpenClaw's agent kept getting stuck in reasoning loops when asked to set reminders. When a user said "Set a reminder at 9:30 PM to wash the socks", the agent would:

1. Invent a `set_reminder` tool that didn't exist in its available tools
2. Confuse `openclaw cron add` (native cron, unreliable) with system cron
3. Convert IST to UTC unnecessarily ("21:30 IST = 16:00 UTC") causing further confusion
4. Loop indefinitely without ever executing anything

**Example of the hallucination loop:**
```
Reasoning: "I need to use the set_reminder tool..."
(NOTE: set_reminder doesn't exist in available tools)

Reasoning: "According to MEMORY.md, use --at '<ISO timestamp>' --delete-after-run"
(NOTE: This references openclaw native cron flags that don't work)

Reasoning: "Actually, I should use the task_manager API..."
(NOTE: API wasn't accessible to the agent)
```

**Root Causes Identified:**
- `MEMORY.md` had conflicting rules (openclaw cron flags alongside system cron rules)
- No clear, step-by-step recipe the agent could follow without reasoning
- The `task_manager`'s `set_reminder` method wrote directly to system crontab instead of the workspace `.crontab` file, causing desync
- The `reminder_cron.py` script (generated by task_manager) only called `print()` — cron discards stdout, so reminders were silently lost

**Fixes Applied:**
1. Created `scripts/reminder-runner.py` — universal one-time reminder script that sends via Telegram and self-cleans
2. Fixed `task_manager/src/tools.py` — `set_reminder()` now writes to workspace `.crontab` and syncs
3. Fixed `_create_reminder_cron_script()` — now sends via Telegram instead of just printing
4. Rewrote `MEMORY.md` with unambiguous step-by-step instructions
5. Added `TZ=Asia/Kolkata` to `/etc/environment` for explicit timezone enforcement

### Phase 2: Task Manager Codebase Audit

After fixing the reminder system, a full audit of the `task_manager/` codebase revealed **15 bugs**, 9 of which would crash at runtime.

#### Critical Bugs Found & Fixed

**1. `TaskManager.complete_task()` return value mismatch**
- `complete_task()` returned `bool` (True/False)
- `tools.py` treated the return as a `Task` object, accessing `.id`, `.title`
- **Impact**: Every API call to complete a task would crash with `AttributeError: 'bool' object has no attribute 'id'`
- **Fix**: Get task first, then call complete

**2. `TaskManager.batch_create_tasks()` didn't exist**
- `tools.py` called `self.task_manager.batch_create_tasks()` but the method was never implemented
- **Impact**: Batch task creation via API or stdio would crash
- **Fix**: Added method to `TaskManager`

**3. `Task` dataclass missing `scheduled_time` field**
- `scheduler.py` accessed `task.scheduled_time` but the field didn't exist
- **Impact**: `get_daily_schedule()` would crash with `AttributeError`
- **Fix**: Added `scheduled_time: Optional[datetime]` to Task dataclass

**4. `TaskManager.get_overdue_tasks()` didn't exist**
- `scheduler.py` called `self.task_manager.get_overdue_tasks()` but only `get_tasks(overdue=True)` existed
- **Impact**: `suggest_schedule()` would crash
- **Fix**: Changed to `get_tasks(overdue=True)`

**5. `task.priority.name` on a string**
- `scheduler.py` and `main.py` used `task.priority.name` but `priority` is stored as a string ("MEDIUM"), not an enum
- **Impact**: Schedule endpoints would return `AttributeError: 'str' object has no attribute 'name'`
- **Fix**: Changed to `str(task.priority)`

**6. `tools/list` stdio handler wrong response shape**
- Handler returned `list(tools.values())` which gave `[[...tool_list...], count]` instead of the tools array
- **Impact**: OpenClaw couldn't discover available tools via stdio
- **Fix**: Changed to `tools_data.get("tools", [])`

**7. `api_list_tasks` ignored `show_completed` parameter**
- The API accepted `show_completed` query param but never passed it to `list_tasks()`
- **Impact**: Users couldn't filter completed tasks via API
- **Fix**: Added param extraction and passing

**8. `api_get_schedule` ignored `date` parameter and crashed on priority**
- The endpoint accepted `date` but always used `due_today=True`
- Used `task.priority.name` which crashes on strings
- **Impact**: Schedule for specific dates impossible, current-date schedule crashed
- **Fix**: Added date filtering + string priority

**9. `Task` dataclass missing `reminders` field**
- `tools.py` accessed `task.reminders` which didn't exist
- **Impact**: `get_task_details()` would crash
- **Fix**: Added `reminders: List[Dict]` field

#### Medium Priority Fixes

**10. Default storage path mismatch**
- `TaskManager.__init__` defaulted to `package_tasks.json`
- `main.py` defaulted to `my_tasks.json`
- **Fix**: Aligned both to `my_tasks.json`

**11. `to_dict()` serialization incomplete**
- Missing `recurrence`, `estimated_duration`, `scheduled_time`, `reminders`
- **Fix**: Added all fields

**12. `test_logging.py` — 2 tests never discovered**
- `test_tools_logger_exists` and `test_task_manager_logger_exists` were indented inside another test method (nested functions)
- pytest never discovered or ran them
- **Fix**: De-indented to class-level methods

#### Low Priority Fixes

**13. Unused dependencies** — Removed `apscheduler` and `pytz` from `requirements.txt` (never imported)
**14. Outdated holidays** — Updated `config.json` holidays from 2024 to 2026
**15. YAML endpoint mismatches** — Fixed `CompleteTask` and `SetReminder` endpoints in `openclaw_skill.yaml` to match actual Flask routes

### Phase 3: Verification

All 15 tests pass (including the 2 previously broken tests):
```
tests/test_api.py::test_api_create_and_list PASSED
tests/test_logging.py::TestLoggingConfiguration (6 tests) PASSED
tests/test_logging.py::TestLoggingOutput (2 tests) PASSED
tests/test_logging.py::TestLoggingLevels (2 tests) PASSED
tests/test_logging.py::TestLoggingHandlers (2 tests) PASSED
tests/test_task_manager.py::test_create_and_get_task PASSED
tests/test_tools.py::test_tools_create_and_list PASSED
======================== 15 passed ========================
```

---

## Reminder System Deep Dive

### How Reminders Work Now

The reminder system uses **system cron + scripts** (never OpenClaw native cron).

```
User: "remind me at 6pm to take socks"
    │
    ▼
Agent parses: WHAT="take socks", WHEN="18:00 IST", TYPE=one-shot
    │
    ▼
Agent adds line to .crontab:
    0 18 24 3 * REMINDER_MSG="take socks" /usr/bin/python3 scripts/reminder-runner.py # REMINDER_x1y2z3
    │
    ▼
Agent runs: crontab .openclaw/workspace/.crontab
    │
    ▼
At 18:00 IST, cron fires reminder-runner.py
    │
    ▼
reminder-runner.py sends "🔔 Reminder: take socks" via Telegram
    │
    ▼
reminder-runner.py removes its own line from .crontab and re-syncs
```

### Why Not OpenClaw Native Cron?

OpenClaw has a built-in cron system (`openclaw cron add`), but it was found to be unreliable:
- CLI (`openclaw cron list`) returns exit code 1 in version 2026.3.13
- Agent hallucinates about the cron flags and syntax
- No reliable way to verify if a cron job was actually created
- MEMORY.md explicitly states: "Never use openclaw native cron for reminders"

### The One-Time Reminder Pattern

The agent has exactly **one reliable path** for setting reminders:

```bash
# Step 1: Add to workspace .crontab
MM HH DD MM * REMINDER_MSG="<message>" /usr/bin/python3 /home/sanchitingale339/.openclaw/workspace/scripts/reminder-runner.py  # REMINDER_<tag>

# Step 2: Sync to system
crontab /home/sanchitingale339/.openclaw/workspace/.crontab
```

The `reminder-runner.py` script:
- Reads message from `REMINDER_MSG` env var
- Sends via `openclaw message send` to Telegram (with 3 retries)
- Removes its own line from `.crontab`
- Re-syncs system crontab

---

## OpenClaw Integration

### Stdio Mode

OpenClaw communicates with TaskManager via JSON-RPC 2.0 over stdin/stdout:

```bash
python3 main.py stdio
```

**Available tools** (via `tools/list`):
- `create_task` — Create a new task
- `create_urgent_task` — Create high-priority task
- `add_to_project` — Add task to project
- `create_recurring_task` — Create recurring task
- `batch_create_tasks` — Create multiple tasks
- `complete_task` — Mark task complete
- `delete_task` — Delete a task
- `list_tasks` — List tasks with filters
- `set_reminder` — Set system cron reminder
- `get_schedule` — Get daily schedule
- `get_schedule_suggestions` — AI schedule suggestions
- `update_routine` — Update work routine
- `add_holiday` — Add holiday
- `add_comp_off` — Add comp-off day
- `list_projects` — List all projects
- `get_task_details` — Get task details

### API Mode

```bash
python3 main.py serve 5000
```

Endpoints documented in README.md. All return JSON with `{ok: bool, data/message}` structure.

### Skill Registration

The `openclaw_skill.yaml` file registers TaskManager as an OpenClaw skill. It defines:
- Tool schemas (parameters, types, required fields)
- API endpoints
- Health check configuration

---

## Timezone Handling

### The Problem

The system runs in IST (`Asia/Kolkata`, UTC+5:30), but OpenClaw's agent sometimes shows UTC times in its reasoning. When the agent converted "9:30 PM IST" to "16:00 UTC" and tried to use the UTC value for cron scheduling, reminders would fire at the wrong time.

### The Solution

**Single source of truth:** All times are IST.

- System timezone: `timedatectl` → `Asia/Kolkata`
- Environment: `TZ=Asia/Kolkata` in `/etc/environment`
- Cron daemon: Uses system timezone (IST)
- All scripts: Use `datetime.now()` (system-local, IST)
- `.crontab` entries: IST times directly

**Rule in MEMORY.md:**
> "When the user says '9:30 PM', use `30 21 * * *` directly — do NOT subtract 5:30"

---

## Current State

### What Works
- Task CRUD (create, read, update, delete, complete)
- Project management
- Priority levels and labels
- AI-powered scheduling based on work routine
- Holiday and comp-off awareness
- System cron reminders via Telegram
- Flask REST API
- JSON-RPC stdio mode for OpenClaw
- 15/15 tests passing

### Known Limitations
- No authentication on API (localhost only)
- Development Flask server (not production-grade)
- Naive datetimes (no explicit timezone objects in code)
- Some overdue tasks in `my_tasks.json` are system-managed (LeetCode, Morning Brew) and should not be manually completed

### Overdue Tasks (as of 2026-03-25)
These are tracked but likely auto-managed:
- "Solve LeetCode problem" (due 2026-03-11) — has daily cron reminders
- "Check Google Cloud Console billing" (due 2026-03-12) — has daily cron reminder
- "Morning Brew 10-day learning program" (due 2026-03-23) — has daily cron generator
- "Buy a 100-page spiral book" (due 2026-03-23) — personal, needs manual completion
- "Take the notebook" (due 2026-03-23) — personal, needs manual completion

---

## Lessons Learned

### 1. AI Agents Need Unambiguous Instructions
The agent's hallucination loop was caused by conflicting instructions in MEMORY.md. When the same file says both "use openclaw cron" and "never use openclaw cron," the agent goes in circles. **One rule, one path, no ambiguity.**

### 2. System Cron > Application Cron
OpenClaw's native cron proved unreliable. System cron is:
- Independent of the application process
- Survives restarts
- Verifiable with `crontab -l`
- Standard Unix — no vendor lock-in

### 3. Self-Cleaning Scripts Prevent Stale Entries
One-time reminders that don't clean up after themselves leave stale crontab entries. The `reminder-runner.py` pattern of removing its own entry after execution keeps the crontab clean.

### 4. Test Discovery Matters
Two tests were silently never running because of an indentation error. Regular test audits (`pytest --collect-only`) catch this.

### 5. Default Values Must Be Consistent
When `TaskManager` defaults to one file and `main.py` defaults to another, bugs hide in plain sight. Always align defaults across entry points.

### 6. Timezone Handling Must Be Explicit
Relying on implicit timezone behavior leads to "works on my machine" bugs. Setting `TZ=Asia/Kolkata` explicitly in the environment and documenting "IST only, never convert" prevents entire classes of bugs.
