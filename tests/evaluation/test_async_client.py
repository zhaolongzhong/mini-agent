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

    async def test_async_client_multi_agent(self, default_chat_model) -> None:
        """
        Test that the agent correctly handles basic input.
        """
        configs = {
            "main": AgentConfig(
                id="main",
                name="main",
                description="Lead coordinator that analyzes tasks, delegates to specialized agents (File Operator and Web Browser), manages information flow, and synthesizes results. Acts as the central hub for team collaboration.",
                instruction="""Coordinate the AI team by analyzing requests, delegating tasks to specialists (File Operator and Web Browser), maintaining context, and synthesizing outputs. Provide clear instructions to agents, facilitate collaboration, and avoid using specialist tools directly.""",
                model=default_chat_model,
                tools=[Tool.Read],
            ),
            "file_operator": AgentConfig(
                id="file_operator",
                name="file_operator",
                description="System operations specialist managing file operations, command execution, and local resources. Collaborates with Orchestrator and Web Browser for task coordination.",
                instruction="""Execute system operations as directed by Orchestrator. Collaborate with Web Browser when tasks require both system operations and internet data. Provide operation feedback, alert on risks, maintain security, and handle errors gracefully.""",
                model=default_chat_model,
                tools=[Tool.Read],
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
