import logging

import pytest

from cue import AgentConfig, AgentManager, RunMetadata, Tool

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.evaluation
class TestClientManager:
    async def test_agent_talks_to_agent(self, default_chat_model, tmp_path: pytest.TempPathFactory) -> None:
        """
        Test that a agent transfer task to another agent.
        """
        agent_manager = AgentManager()
        agent_a_config = AgentConfig(
            id="agent_a",
            name="agent_a",
            is_primary=True,
            instruction="Your name is agent_a",
            model=default_chat_model,
            tools=[Tool.Read],
        )

        agent_b_config = AgentConfig(
            id="agent_b",
            name="agent_b",
            instruction="Your name is agent_b",
            model=default_chat_model,
            tools=[Tool.Read, Tool.Write],
        )
        agent_a = agent_manager.register_agent(agent_a_config)
        agent_b = agent_manager.register_agent(agent_b_config)
        agent_a.add_tool_to_agent(agent_a.chat_with_agent)
        agent_b.add_tool_to_agent(agent_b.chat_with_agent)

        try:
            file_name = "fibo.py"
            file_path = tmp_path / file_name
            instruction = f"Can you create a fibonacci function named fibonacci at {file_path}?"
            response = await agent_manager.run(agent_a.id, instruction, run_metadata=RunMetadata(max_turns=8))
            logger.debug(f"Response: {response}")
            assert response is not None, "Expected a non-None response."
            assert file_path.exists(), f"Expected file '{file_path}' to be created."

            content = file_path.read_text()
            logger.debug(f"File Content: {content}")
            assert agent_manager.active_agent.id == "agent_a", "Active agent should be agent_a"

            assert "def fibonacci" in content, "Fibonacci function not found in the created file."
        finally:
            await agent_manager.clean_up()
