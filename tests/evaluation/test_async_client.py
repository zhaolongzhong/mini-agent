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
        client = AsyncCueClient()
        await client.initialize([agent_config])

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
        client = AsyncCueClient()
        await client.initialize([agent_config])

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

    async def test_async_client_multi_agent(self) -> None:
        """
        Test that the agent correctly handles basic input.
        """
        configs = {
            "main": AgentConfig(
                id="main",
                name="main",
                description="Lead coordinator that analyzes tasks, delegates to specialized agents (File Operator and Web Browser), manages information flow, and synthesizes results. Acts as the central hub for team collaboration.",
                instruction="""Coordinate the AI team by analyzing requests, delegating tasks to specialists (File Operator and Web Browser), maintaining context, and synthesizing outputs. Provide clear instructions to agents, facilitate collaboration, and avoid using specialist tools directly.""",
                model=ChatModel.GPT_4O_MINI,
                temperature=0.8,
                max_tokens=2000,
                tools=[Tool.FileRead],
            ),
            "file_operator": AgentConfig(
                id="file_operator",
                name="file_operator",
                description="System operations specialist managing file operations, command execution, and local resources. Collaborates with Orchestrator and Web Browser for task coordination.",
                instruction="""Execute system operations as directed by Orchestrator. Collaborate with Web Browser when tasks require both system operations and internet data. Provide operation feedback, alert on risks, maintain security, and handle errors gracefully.""",
                model=ChatModel.GPT_4O_MINI,
                tools=[
                    Tool.FileRead,
                ],
            ),
        }
        client = AsyncCueClient()
        await client.initialize(list(configs.values()))

        try:
            agent_ids = client.get_agent_ids()
            # Send message using active agent
            new_agent_id = agent_ids[0]
            assert new_agent_id == "main"
            response = await client.send_message("Hello there, who am I talking to? What is your id?")
            response_text = str(response).lower()
            assert "main" in response_text

            # Switch active agent
            new_agent_id = agent_ids[1]
            assert new_agent_id == "file_operator"
            client.set_active_agent(new_agent_id)
            response = await client.send_message("Hello there, who am I talking to? What is your id?")
            assert "file_operator" in str(response).lower()

        finally:
            await client.cleanup()
