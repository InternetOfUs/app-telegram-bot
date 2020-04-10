import random
from unittest import TestCase
from uuid import uuid4

from eat_together_bot.models import Task


class TestTask(TestCase):
    def test_repr(self):
        task = Task(
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None,
            str(uuid4()) if random.randint(0, 100) % 2 == 0 else None
        )
        task_repr = task.to_repr()
        self.assertEqual(Task.from_repr(task_repr), task)
