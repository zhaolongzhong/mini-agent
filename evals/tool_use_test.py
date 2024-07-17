import shutil
import subprocess
import tempfile

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
    await manager.create_agents(model=ChatModel.GPT_4O)
    return manager


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_write_file(task_family: TaskFamily, temp_dir: str):
    for task in task_family.get_tasks().values():
        # refresh agent for each task
        manager = AgentManager(is_test=True)
        await manager.create_agents(model=ChatModel.GPT_4O)

        # set up task
        init_cmd = task["start"]["code"]
        if init_cmd:
            run_command(f"cd {temp_dir} && {init_cmd}")

        instruction = task_family.get_instructions(task, temp_dir)
        response = await manager.handle_input(instruction)
        print(f"agent response: {response}")
        submission = response

        # check if there is a check command
        check_cmd = task["evaluation"]["check"]
        if check_cmd:
            output = run_command(f"cd {temp_dir} && {check_cmd}")
            submission = output
        score = task_family.score(task, submission)
        assert score == 1.0


def run_command(cmd):
    print(f"Running: {cmd}", flush=True)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
    if result.returncode != 0:
        raise Exception(f"Command exited with non-zero exit code: {result.returncode}")

    if result.stdout:
        print(f"[stdout]\n{result.stdout}")
        return result.stdout

    return ""
