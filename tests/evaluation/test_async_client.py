import logging
import shutil
import tempfile

import pytest

from cue import AgentConfig, AsyncCueClient, ChatModel, StorageType, Tool

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def agent_config() -> AgentConfig:
    """
    Fixture to create and return an AgentConfig instance.
    """
    return AgentConfig(
        id="main",
        name="MainAgent",
        storage_type=StorageType.IN_MEMORY,
        model=ChatModel.GPT_4O_MINI,
        tools=[
            Tool.FileRead,
            Tool.FileWrite,
        ],
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
@pytest.mark.evaluation
class TestClientManager:
    async def test_async_client(self, agent_config: AgentConfig) -> None:
        """
        Test that the agent correctly handles basic input.
        """
        client = AsyncCueClient(config=agent_config)
        await client.initialize()

        try:
            response = await client.send_message(
                "Hello, Cue! ### This is basic test, respond must include 'Hello, World!'"
            )
            logger.debug(f"Response: {response}")
            assert response is not None, "Expected a non-None response."
            assert "Hello, World!" in response, "Response does not contain 'Hello, World!'."
        finally:
            await client.cleanup()

    async def test_basic_tool_use(self, agent_config: AgentConfig, tmp_path: pytest.TempPathFactory) -> None:
        """
        Test the basic usage of tools by the agent, specifically file creation and content verification.
        """
        client = AsyncCueClient(config=agent_config)
        await client.initialize()

        file_name = "fibo.py"
        file_path = tmp_path / file_name
        instruction = f"Under {tmp_path}, can you create a fibonacci function in {file_name}?"

        response = await client.send_message(instruction)
        logger.debug(f"Response: {response}")

        assert response is not None, "Expected a non-None response from handle_input."
        assert "fibo" in response.lower(), "Response does not mention 'fibo'."
        assert file_path.exists(), f"Expected file '{file_path}' to be created."

        content = file_path.read_text()
        logger.debug(f"File Content: {content}")

        assert "def fibonacci" in content, "Fibonacci function not found in the created file."
