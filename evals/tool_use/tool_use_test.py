import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from cue import Agent, AgentConfig, AgentManager, ChatModel, CompletionResponse, FeatureFlag, StorageType, Tool

from .tool_use import ToolTaskFamily


@pytest.fixture
def task_family():
    return ToolTaskFamily()


@pytest.fixture(scope="function")
def agent_config() -> AgentConfig:
    """
    Fixture to create and return an AgentConfig instance.
    """
    return AgentConfig(
        name="cue_cli",
        model=ChatModel.GPT_4O_MINI,
        temperature=0.8,
        max_tokens=2000,
        conversation_id="",
        feature_flag=FeatureFlag(is_cli=True, is_eval=False),
        storage_type=StorageType.IN_MEMORY,
        tools=[Tool.FileRead, Tool.ShellTool, Tool.FileWrite],
        is_test=True,
    )


@pytest.fixture(scope="function")
def temp_dir():
    dirpath = tempfile.mkdtemp()
    print(f"Created temporary directory: {dirpath}")
    yield dirpath
    shutil.rmtree(dirpath)
    print(f"Deleted temporary directory: {dirpath}")


@pytest.mark.asyncio
@pytest.mark.evals
async def test_tool_use(task_family: ToolTaskFamily, temp_dir: str):
    results = []
    model = ChatModel.GPT_4O_MINI
    for task in task_family.get_tasks().values():
        # refresh agent for each task
        agent_config = AgentConfig(
            name="cue_cli",
            model=ChatModel.GPT_4O_MINI,
            temperature=0.8,
            max_tokens=2000,
            conversation_id="",
            feature_flag=FeatureFlag(is_cli=True, is_eval=False),
            storage_type=StorageType.IN_MEMORY,
            tools=[Tool.FileRead, Tool.ShellTool, Tool.FileWrite],
            is_test=True,
        )
        manager = AgentManager(config=agent_config)
        agent: Agent = await manager.create_agents(agent_config)

        # set up task
        init_cmd = task["start"]["code"]
        if init_cmd:
            run_command(f"cd {temp_dir} && {init_cmd}")

        instruction = task_family.get_instructions(task, temp_dir)
        response = await agent.send_message(instruction)
        metadata = agent.get_metadata()
        print(f"task:{task['id']}, metadata: {metadata}, agent response: {response}")
        if isinstance(response, CompletionResponse):
            submission = response.get_text()
        else:
            submission = str(response)

        # check if there is a check command
        check_cmd = task["evaluation"]["check"]
        if check_cmd:
            output = run_command(f"cd {temp_dir} && {check_cmd}")
            submission = output
        score = task_family.score(task, str(submission))
        results.append(
            {
                "task_id": task["id"],
                "model": model.model_id,
                "submission": submission,
                "score": score,
                "metadata": metadata.model_dump() if metadata else None,
            }
        )
    result_path = Path(__file__).parent / "results/test_tool_use.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
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
