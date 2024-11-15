import asyncio
import logging

import pytest

from cue import AgentConfig, AsyncCueClient
from cue.tools._tool import Tool
from cue.schemas.feature_flag import FeatureFlag

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def agent_config(default_chat_model) -> AgentConfig:
    """Fixture to create and return an AgentConfig instance."""
    return AgentConfig(
        id="main",
        is_primary=True,
        model=default_chat_model,
        tools=[Tool.Browse],
        feature_flag=FeatureFlag(is_test=True),
    )


@pytest.mark.asyncio
@pytest.mark.evaluation
class TestClientManager:
    async def test_async_client(self, agent_config: AgentConfig) -> None:
        client = AsyncCueClient()
        try:
            await client.initialize([agent_config])
            response = await client.send_message(
                "Hello, there ### This is basic test, respond must include 'Hello, World!'"
            )
            logger.debug(f"Response: {response}")
            assert response is not None, "Expected a non-None response."
            assert "Hello, World!" in response, "Response does not contain 'Hello, World!'."
        finally:
            await client.cleanup()
            await asyncio.sleep(0.1)  # Give time for cleanup tasks to complete

    async def test_async_client_multi_agent(self, default_chat_model, tmp_path: pytest.TempPathFactory) -> None:
        configs = {
            "main": AgentConfig(
                id="main",
                is_primary=True,
                description="Lead coordinator that analyzes tasks, delegates to specialized agents.",
                instruction="Coordinate the AI team by analyzing requests, delegating tasks to specialists.",
                model=default_chat_model,
                tools=[Tool.Coordinate],
            ),
            "file_operator": AgentConfig(
                id="file_operator",
                description="System operations specialist managing file operations.",
                instruction="Execute system operations as directed by main or coordinator agent.",
                model=default_chat_model,
                tools=[Tool.Coordinate, Tool.Edit],
            ),
        }

        client = AsyncCueClient()
        try:
            await client.initialize(list(configs.values()))

            agent_ids = client.get_agent_ids()
            new_agent_id = agent_ids[0]
            assert new_agent_id == "main"
            response = await client.send_message("Hello there, who am I talking to? What is your id?")
            response_text = str(response).lower()
            assert "main" or "primary" in response_text

            file_name = "fibo.py"
            file_path = tmp_path / file_name
            instruction = f"Under {tmp_path}, can you create a fibonacci function in {file_name}?"

            response = await client.send_message(instruction)
            logger.debug(f"Response: {response}")

            assert response is not None, "Expected a non-none response from handle_input."
            assert "fibo" in response.lower(), "Response does not mention 'fibo'."
            assert file_path.exists(), f"Expected file '{file_path}' to be created."

            content = file_path.read_text()
            logger.debug(f"File Content: {content}")

            assert "def fibonacci" in content, "Fibonacci function not found in the created file."
        finally:
            await client.cleanup()
            await asyncio.sleep(0.1)  # Give time for cleanup tasks to complete
