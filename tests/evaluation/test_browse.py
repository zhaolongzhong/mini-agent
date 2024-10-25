import logging
from typing import List

import pytest

from cue import AgentConfig, AsyncCueClient, Tool

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def agent_config(default_chat_model) -> AgentConfig:
    """Fixture to create and return an AgentConfig instance."""
    return AgentConfig(
        id="main",
        name="MainAgent",
        model=default_chat_model,
        tools=[Tool.Browse],
        is_test=True,
    )


@pytest.mark.asyncio
@pytest.mark.evaluation
class TestBrowseTool:
    def get_key_terms(self) -> List[str]:
        return ["example domain", "This domain is for use in illustrative examples in documents."]

    async def test_example(self, agent_config: AgentConfig) -> None:
        """Test that the agent can successfully browse and comprehend the Wikipedia AI article."""
        client = AsyncCueClient()
        await client.initialize([agent_config])

        try:
            response = await client.send_message("Can you browse https://example.com/")
            logger.debug(f"Response: {response}")

            # Basic response validation
            assert response is not None, "Expected a non-None response"
            assert len(response) > 100, "Response too short for a meaningful summary"

            # Content-specific assertions
            key_terms = self.get_key_terms()
            found_terms = [term for term in key_terms if term.lower() in response.lower()]
            assert len(found_terms) >= 1, f"Response should contain at least 1 key terms. Found: {found_terms}"
        finally:
            await client.cleanup()