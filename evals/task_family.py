# https://github.com/METR/task-standard/blob/main/template/template.py
from typing import TypedDict


class Task(TypedDict):
    pass


class TaskFamily:
    standard_version = "0.2.3"

    @staticmethod
    def install() -> None:
        pass

    @staticmethod
    def get_tasks() -> dict[str, dict]:
        raise NotImplementedError("Must implement get_tasks")

    @staticmethod
    def get_instructions(t: dict) -> str:
        raise NotImplementedError("Must implement get_instructions")

    @staticmethod
    def start(t: Task) -> None:
        pass

    @staticmethod
    def score(t: str, submission: str) -> float:
        raise NotImplementedError("Must implement score")

    @staticmethod
    def teardown(t: Task) -> None:
        pass
