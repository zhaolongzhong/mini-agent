import logging

import pytest

from cue import AgentConfig, AgentManager, ChatModel, StorageType, Tool

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


@pytest.mark.asyncio
@pytest.mark.evaluation
class TestAgentManager:
    async def test_handle_input(self, agent_config: AgentConfig) -> None:
        """
        Test that the agent correctly handles basic input.
        """
        agent_manager = AgentManager(config=agent_config)
        await agent_manager.create_agents(agent_config)

        input_prompt = "This is basic test, respond with 'Hello, World!'"
        response = await agent_manager.handle_input(input_prompt)

        assert response is not None, "Expected a non-None response from handle_input."
        assert "Hello, World!" in response, "Response does not contain 'Hello, World!'."

    async def test_basic_tool_use(self, agent_config: AgentConfig, tmp_path: pytest.TempPathFactory) -> None:
        """
        Test the basic usage of tools by the agent, specifically file creation and content verification.
        """
        agent_manager = AgentManager(config=agent_config)
        await agent_manager.create_agents(agent_config)

        file_name = "fibo.py"
        file_path = tmp_path / file_name
        input_prompt = f"Under {tmp_path}, can you create a fibonacci function in {file_name}?"

        response = await agent_manager.handle_input(input_prompt)
        logger.debug(f"Response: {response}")

        assert response is not None, "Expected a non-None response from handle_input."
        assert "fibo" in response.lower(), "Response does not mention 'fibo'."
        assert file_path.exists(), f"Expected file '{file_path}' to be created."

        content = file_path.read_text()
        logger.debug(f"File Content: {content}")

        assert "def fibonacci" in content, "Fibonacci function not found in the created file."
