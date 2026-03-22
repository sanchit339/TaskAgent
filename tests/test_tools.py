from pathlib import Path
from task_manager_package.task_manager import TaskManager
from scheduler import SchedulerConfig, AIScheduler
from reminder import ReminderSystem
from tools import TaskTools


def test_tools_create_and_list(tmp_path):
    storage = tmp_path / "tasks.json"
    tm = TaskManager(str(storage))
    sc = SchedulerConfig(str(tmp_path / "config.json"))
    sch = AIScheduler(tm, sc)
    rem = ReminderSystem(tm)
    tools = TaskTools(tm, sch, rem)

    # create tasks via tools
    result = tools.create_task(title="API test task", description="desc", project="Inbox")
    # result should be a dict with 'task' and 'message'
    assert isinstance(result, dict)
    assert "task" in result
    assert "message" in result
    assert "✅ Task created" in result["message"]

    # list tasks compact
    resp = tools.list_tasks(limit=10, offset=0)
    assert isinstance(resp, dict)
    assert "tasks" in resp
    assert resp["total"] >= 1
    # check task fields
    task0 = resp["tasks"][0]
    assert set(["id", "title", "project", "priority", "completed", "due_date"]).issubset(set(task0.keys()))
