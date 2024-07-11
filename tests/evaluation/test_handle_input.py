import os
import shutil
import tempfile

import pytest
from agent_manager import AgentManager
from llm_client.llm_model import ChatModel
from memory.memory import StorageType
from schemas.agent import AgentConfig
from tools.tool_manager import Tool


@pytest.fixture(scope="function")
def temp_dir():
    dirpath = tempfile.mkdtemp()
    print(f"Created temporary directory: {dirpath}")
    yield dirpath
    shutil.rmtree(dirpath)
    print(f"Deleted temporary directory: {dirpath}")


@pytest.fixture(scope="function")
def agent_config(temp_dir):
    return AgentConfig(
        id="main",
        name="MainAgent",
        storage_type=StorageType.FILE,
        model=ChatModel.GPT_4O,
        tools=[
            Tool.FileRead,
            Tool.FileWrite,
            Tool.CheckFolder,
            Tool.CodeInterpreter,
            Tool.ShellTool,
        ],
    )


@pytest.mark.filterwarnings("ignore::pydantic.warnings.PydanticDeprecatedSince20")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_handle_input(agent_config: AgentConfig, monkeypatch):
    agent_manager = AgentManager(is_test=True)
    await agent_manager.create_agents(model=ChatModel.LLAMA3_70B_8192_GROQ)
    response = await agent_manager.handle_input("This is basic test, respond with 'Hello, World!'")
    assert response is not None
    assert "Hello, World!" in response


@pytest.mark.filterwarnings("ignore::pydantic.warnings.PydanticDeprecatedSince20")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_basic_tool_use(agent_config: AgentConfig, monkeypatch, temp_dir):
    agent_manager = AgentManager(is_test=True)
    await agent_manager.create_agents(model=ChatModel.LLAMA3_70B_8192_GROQ)

    # temp_dir = "tests/temp"
    file_path = os.path.join(temp_dir, "fibo.py")

    response = await agent_manager.handle_input(f"Under {temp_dir}, can you create a fibonacci function to fibo.py?")
    print(f"Response: {response}")

    assert response is not None
    assert "fibo" in response.lower()

    assert os.path.exists(file_path), f"Expected file {file_path} to be created"

    # Optionally, read the file to verify its content (if needed)
    with open(file_path) as file:
        content = file.read()
        print(f"File Content: {content}")
        assert "def fibonacci" in content

    if os.path.exists(file_path):
        os.remove(file_path)
