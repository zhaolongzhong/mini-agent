import logging

import pytest

from cue import AgentConfig, AsyncCueClient, Tool

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def agent_config(default_chat_model) -> AgentConfig:
    """
    Fixture to create and return an AgentConfig instance.
    """
    return AgentConfig(
        id="main",
        name="MainAgent",
        is_primary=True,
        model=default_chat_model,
        tools=[],
        is_test=True,
    )


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
                "Hello, there ### This is basic test, respond must include 'Hello, World!'"
            )
            logger.debug(f"Response: {response}")
            assert response is not None, "Expected a non-None response."
            assert "Hello, World!" in response, "Response does not contain 'Hello, World!'."
        finally:
            await client.cleanup()

    async def test_async_client_multi_agent(self, default_chat_model, tmp_path: pytest.TempPathFactory) -> None:
        """
        Test that the agent correctly handles basic input.
        """
        configs = {
            "main": AgentConfig(
                id="main",
                name="main",
                is_primary=True,
                description="Lead coordinator that analyzes tasks, delegates to specialized agents. Acts as the central hub for team collaboration.",
                instruction="Coordinate the AI team by analyzing requests, delegating tasks to specialists (File Operator and Web Browser), maintaining context, and synthesizing outputs. Provide clear instructions to agents, facilitate collaboration, and avoid using specialist tools directly."
                "",
                model=default_chat_model,
                tools=[],
            ),
            "file_operator": AgentConfig(
                id="file_operator",
                name="file_operator",
                description="System operations specialist managing file operations.",
                instruction="Execute system operations as directed by main or coordinator agent.",
                model=default_chat_model,
                tools=[Tool.Edit],
            ),
        }
        client = AsyncCueClient()
        await client.initialize(list(configs.values()))

        try:
            agent_ids = client.get_agent_ids()
            new_agent_id = agent_ids[0]
            assert new_agent_id == "main"
            response = await client.send_message("Hello there, who am I talking to? What is your id?")
            response_text = str(response).lower()
            assert "main" in response_text

            # Test coordination
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

        finally:
            await client.cleanup()
