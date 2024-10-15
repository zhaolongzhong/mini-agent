import asyncio
import logging
import sys
from typing import Optional

from ._agent import Agent
from .schemas import AgentConfig, ErrorResponse, Metadata
from .utils.cli_utils import progress_indicator

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(
        self,
        config: Optional[AgentConfig],
    ):
        logger.info("AgentManager initialized")
        self.default_config = config
        self.agents = {}

    async def set_up(self, config: AgentConfig):
        return await self.create_agents(config)

    async def clean_up(self):
        pass

    async def create_agents(self, config: AgentConfig) -> Agent:
        self.agent: Agent = await self.create_agent(config=config)
        return self.agent

    async def create_agent(
        self,
        config: AgentConfig,
    ):
        if id in self.agents:
            logger.warning(f"Agent with id {id} already exists, return existing agent.")
            return self.agents[id]
        agent = await Agent.create(config=config)
        self.agents[agent.id] = agent
        logger.info(f"Created agent, available agents: {list(self.agents.keys())}")
        return agent

    async def handle_input(self, user_input: str):
        if user_input:
            indicator = None
            if self.default_config.is_test is False:
                indicator = asyncio.create_task(progress_indicator())
            try:
                response = await self.agent.send_message(user_input)
                if indicator:
                    indicator.cancel()
                logger.debug(f"[main] {response}")
                if isinstance(response, ErrorResponse):
                    return f"[Agent]: There is an error. Error: {response.model_dump_json()}"
                else:
                    return f"[Agent]: {response.get_text()}"
            finally:
                if indicator:
                    try:
                        await indicator
                    except asyncio.CancelledError:
                        sys.stdout.write("\r")
                        sys.stdout.flush()
        return None

    def get_metadata(self) -> Optional[Metadata]:
        if self.agent is None:
            return None
        return self.agent.metadata
