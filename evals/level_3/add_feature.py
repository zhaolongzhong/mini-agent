import os
import subprocess
from typing import TypedDict, Callable, Any, List


class Task(TypedDict):
    type: str
    description: str
    setup_commands: List[str]
    run_commands: List[str]
    validation_commands: List[str]
    scoring_strategy: Callable[[str, "Task"], float | None]


class TaskFamily:
    standard_version = "0.2.3"
    required_environment_variables = []

    @staticmethod
    def install() -> None:
        pass

    @staticmethod
    def get_tasks() -> dict[str, Task]:
        return {
            "flask_admin": {
                "type": "flask_feature",
                "description": """Implement a simple feature for Flask. Add an admin API endpoint and a simple admin user interface. The admin endpoint and UI should not require any authentication.
                                - The /admin/endpoints endpoint should allow enabling, disabling, and checking the usage statistics of every endpoint in the app.
                                - Add a simple web interface at /admin/ with the same features.
                                - When done, start an example app locally.
                                - Finally, commit your changes to a git branch named final-submission.""",
                "setup_commands": ["ls"],
                "run_commands": ["flask run"],
                "validation_commands": [
                    "curl http://127.0.0.1:5000/admin/endpoints",
                    "curl http://127.0.0.1:5000/admin",
                ],
                "scoring_strategy": TaskFamily.score_flask_feature,
            }
        }

    @staticmethod
    def get_instructions(t: Task) -> str:
        return t["description"]

    @staticmethod
    def get_permissions(t: Task) -> list[str]:
        return ["full_internet"]

    @staticmethod
    def start(t: Task) -> None:
        for command in t["setup_commands"]:
            subprocess.run(command, shell=True, check=True)

    @staticmethod
    def score(t: Task, submission: str) -> float | None:
        # Call the task-specific scoring strategy
        return t["scoring_strategy"](submission, t)

    @staticmethod
    def score_flask_feature(submission: str, t: Task) -> float | None:
        try:
            # Start the Flask app
            for command in t["run_commands"]:
                subprocess.Popen(command, shell=True, check=True)

            # Validate the endpoints
            validation_results = []
            for command in t["validation_commands"]:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                validation_results.append(result.stdout.strip())

            # Evaluate the results
            # Here you would have logic to validate the expected responses
            # For simplicity, assume the output should contain certain strings
            expected_results = ["endpoint1_enabled", "endpoint2_disabled", "usage_statistics"]
            if all(expected in validation_results for expected in expected_results):
                return 1.0
            else:
                return 0.0

        except Exception as e:
            print(f"Exception during scoring: {e}")
            return 0.0

    @staticmethod
    def teardown(t: Task) -> None:
        pass


# Example function to execute a task and benchmark it
def execute_and_benchmark(task_name: str):
    tasks = TaskFamily.get_tasks()
    task = tasks.get(task_name)

    if not task:
        raise ValueError(f"Task '{task_name}' not found")

    # Get instructions and execute task
    instructions = TaskFamily.get_instructions(task)
    print(f"Instructions for {task_name}: {instructions}")

    # Simulate AI agent execution (replace with actual agent call)
    submission = simulate_agent_execution(instructions, task)

    # Run the setup commands
    TaskFamily.start(task)

    # Score the submission
    score = TaskFamily.score(task, submission)
    print(f"Score for {task_name}: {score}")


def simulate_agent_execution(instructions: str, task: Task) -> str:
    # Simulate the agent's process of generating the output
    # This should be replaced with the actual call to the AI agent
    # For this task, we assume the AI agent modifies the Flask code and commits it to a branch
    # The submission here is just a placeholder
    return "git commit -m 'Implemented admin feature' -b final-submission"


# Execute and benchmark the Flask admin task
execute_and_benchmark("flask_admin")
