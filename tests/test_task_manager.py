import json
from pathlib import Path
from task_manager_package.task_manager import TaskManager


def test_create_and_get_task(tmp_path):
    storage = tmp_path / "tasks.json"
    tm = TaskManager(str(storage))

    # create a task
    task = tm.create_task(title="unit test task", description="desc")
    assert task.title == "unit test task"
    assert tm.get_task(task.id) is not None

    # save and reload
    tm.save()
    tm2 = TaskManager(str(storage))
    found = tm2.get_task(task.id)
    assert found is not None
    assert found.title == task.title
