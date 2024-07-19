import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from agent_manager import AgentManager
from llm_client.llm_model import ChatModel

from evals.task_family import TaskFamily
from evals.tool_use import ToolTaskFamily


@pytest.fixture
def task_family():
    return ToolTaskFamily()


@pytest.fixture(scope="function")
def temp_dir():
    dirpath = tempfile.mkdtemp()
    print(f"Created temporary directory: {dirpath}")
    yield dirpath
    shutil.rmtree(dirpath)
    print(f"Deleted temporary directory: {dirpath}")


@pytest_asyncio.fixture
async def agent_manager() -> AgentManager:
    manager = AgentManager(is_test=True)
    await manager.create_agents(model=ChatModel.GPT_4O_MINI)
    return manager


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_tool_use(task_family: TaskFamily, temp_dir: str):
    results = []
    model = ChatModel.GPT_4O_MINI
    for task in task_family.get_tasks().values():
        # refresh agent for each task
        manager = AgentManager(is_test=True)
        await manager.create_agents(model=model)

        # set up task
        init_cmd = task["start"]["code"]
        if init_cmd:
            run_command(f"cd {temp_dir} && {init_cmd}")

        instruction = task_family.get_instructions(task, temp_dir)
        response = await manager.handle_input(instruction)
        metadata = manager.get_metadata()
        print(f"task:{task['id']}, metadata: {metadata}, agent response: {response}")
        submission = response

        # check if there is a check command
        check_cmd = task["evaluation"]["check"]
        if check_cmd:
            output = run_command(f"cd {temp_dir} && {check_cmd}")
            submission = output
        score = task_family.score(task, submission)
        results.append(
            {
                "task_id": task["id"],
                "model": model.model_id,
                "submission": submission,
                "score": score,
                "metadata": metadata.model_dump() if metadata else None,
            }
        )
        assert score == 1.0
    result_path = Path(__file__).parent / "results/test_tool_use.json"
    with open(result_path, "w") as result_file:
        json.dump(results, result_file, indent=4)


def run_command(cmd):
    print(f"Running: {cmd}", flush=True)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
    if result.returncode != 0:
        raise Exception(f"Command exited with non-zero exit code: {result.returncode}")

    if result.stdout:
        print(f"[stdout]\n{result.stdout}")
        return result.stdout

    return ""
