import random
from datetime import datetime
from unittest import TestCase
from uuid import uuid4

from eat_together_bot.models import Task


class TestTask(TestCase):
    def test_repr(self):
        task = Task(
            str(uuid4()),
            str(uuid4()),
            datetime(random.randint(2000, 2020), random.randint(1, 12), random.randint(1, 28), random.randint(0, 23),
                     random.randint(0, 59)) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            datetime(random.randint(2000, 2020), random.randint(1, 12), random.randint(1, 28), random.randint(0, 23),
                     random.randint(0, 59)) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None
        )
        task_repr = task.to_repr()
        self.assertEqual(Task.from_repr(task_repr), task)

    def test_parsing_from_service_api(self):
        name = "pippo"
        description = "pluto"
        app_id = "appId"
        raw = {
            "taskId": "task-id",
            "_creationTs": 1577833200,
            "_lastUpdateTs": 1577833200,
            "taskTypeId": "task_type_id",
            "requesterId": "requester_id",
            "appId": app_id,
            "goal": {
                "name": name,
                "description": description
            },
            "startTs": 1577833100,
            "endTs": 1577833300,
            "deadlineTs": 1577833350,
            "norms": [],
            "attributes": []
        }
        task = Task.from_service_api_task_repr(raw)
        self.assertIsInstance(task, Task)
        self.assertEqual(name, task.name)
        self.assertEqual(description, task.description)
