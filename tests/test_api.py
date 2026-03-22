import json
from pathlib import Path
import pytest

import main as main_mod
from task_manager_package.task_manager import TaskManager
from scheduler import SchedulerConfig, AIScheduler
from reminder import ReminderSystem
from tools import TaskTools


def test_api_create_and_list(tmp_path, monkeypatch):
    # Prepare isolated components using a temporary storage
    storage = tmp_path / "tasks.json"
    tm = TaskManager(str(storage))
    sc = SchedulerConfig(str(tmp_path / "config.json"))
    sch = AIScheduler(tm, sc)
    rem = ReminderSystem(tm)
    tools = TaskTools(tm, sch, rem)

    # Monkeypatch module-level globals in main to use the test instances
    monkeypatch.setattr(main_mod, "task_manager", tm)
    monkeypatch.setattr(main_mod, "scheduler", sch)
    monkeypatch.setattr(main_mod, "reminder_system", rem)
    monkeypatch.setattr(main_mod, "task_tools", tools)

    app = main_mod.create_app()
    client = app.test_client()

    # Create a task via API
    resp = client.post('/api/tasks', json={"title": "api test task", "description": "desc"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "data" in data
    assert "task" in data["data"]
    task = data["data"]["task"]
    assert task["title"] == "api test task"

    # List tasks via API
    resp2 = client.get('/api/tasks?limit=10&offset=0')
    assert resp2.status_code == 200
    tasks_list = resp2.get_json()
    # API may return a wrapped envelope {ok: True, data: {...}} or direct result
    if tasks_list.get("ok") is True and "data" in tasks_list:
        payload = tasks_list["data"]
    else:
        payload = tasks_list

    assert "tasks" in payload
    assert isinstance(payload["tasks"], list)
    assert payload["total"] >= 1
