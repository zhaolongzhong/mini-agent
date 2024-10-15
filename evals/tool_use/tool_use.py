from evals.task_family import TaskFamily


class Task:
    id: str
    prompt: str
    start: dict[str, str] = {}
    expect: str


class ToolTaskFamily(TaskFamily):
    @staticmethod
    def get_tasks() -> dict[str, Task]:
        return {
            "write": {
                "id": "write",
                "prompt": "Write a fibonacci function 'def fibo(num):`at fibo.py",
                "start": {"code": ""},
                "evaluation": {"check": "cat fibo.py"},
                "expect": "def fibo(num)",
            },
            "read": {
                "id": "read",
                "prompt": "Read the fibonacci function from fibo.py",
                "start": {"code": "echo 'def fibo(num):' > fibo.py"},
                "evaluation": {"check": ""},
                "expect": "def fibo(num)",
            },
            "shell": {
                "id": "shell",
                "prompt": "Can you run test.sh?",
                "start": {"code": "echo 'echo hello world' > test.sh && chmod +x test.sh"},
                "evaluation": {"check": ""},
                "expect": "hello world",
            },
            "python": {
                "id": "python",
                "prompt": "Can you use run python script tool to run test.py?",
                "start": {"code": "echo 'print(\"hello world\")' > test.py"},
                "evaluation": {"check": ""},
                "expect": "hello world",
            },
        }

    @staticmethod
    def get_instructions(t: Task, temp_dir: str) -> str:
        return f"Under {temp_dir}, {t['prompt']}'"

    @staticmethod
    def score(t: dict, submission: str) -> float:
        print(f"Scoring {t['id']}: {submission}")
        return 1.0 if t["expect"] in submission else 0.0
