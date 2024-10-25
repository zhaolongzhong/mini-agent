from typing import Dict, List, Optional

from ._agent_manager import AgentManager
from .cli._agents import get_agent_configs
from .llm import ChatModel
from .schemas import AgentConfig, CompletionResponse, RunMetadata
from .tools._tool import Tool
from .utils.logs import _logger, setup_logging

setup_logging()


class AsyncCueClient:
    def __init__(self):
        self.logger = _logger
        self.agent_manager = AgentManager()
        self.agents: Dict[str, AgentConfig] = {}
        self.active_agent_id: Optional[str] = None
        self.run_metadata = RunMetadata()

    def _create_default_config(self) -> AgentConfig:
        return AgentConfig(
            id="default_agent",
            name="default_agent",
            model=ChatModel.GPT_4O_MINI,
            temperature=0.8,
            max_tokens=2000,
            conversation_id="",
            tools=[
                Tool.Read,
                Tool.Write,
                Tool.Bash,
            ],
        )

    async def initialize(self, configs: Optional[List[AgentConfig]] = None):
        """Initialize the client with multiple agents."""
        self.logger.info("Initializing AsyncCueClient with multiple agents")

        active_agent_id = None
        if not configs:
            configs_dict, main_agent_id = get_agent_configs()
            configs = configs_dict
            active_agent_id = main_agent_id
        else:
            active_agent_id = configs[0].id
        self.active_agent_id = active_agent_id

        for config in configs:
            agent_id = config.id
            self.agents[agent_id] = self.agent_manager.register_agent(config)
            if len(configs) > 1:
                # only add it when there are multiple agents
                self.agents[agent_id].add_tool_to_agent(self.agents[agent_id].chat_with_agent)

        if not self.agents:
            # Fallback to default configuration if no agents are configured
            default_config = self._create_default_config()
            self.agents[default_config.id] = self.agent_manager.register_agent(default_config)
            self.active_agent_id = default_config.id

        self.logger.info(f"Initialized with {len(self.agents)} agents. Active agent: {self.active_agent_id}")

    async def send_message(self, message: str, agent_id: Optional[str] = None) -> str:
        """Send a message to a specific agent or the active agent."""
        target_agent_id = agent_id or self.active_agent_id
        if not target_agent_id or target_agent_id not in self.agents:
            raise ValueError(f"Invalid agent ID: {target_agent_id}")

        self.logger.debug(f"Sending message to agent {target_agent_id}: {message}")
        self.run_metadata.user_messages.append(message)

        response = await self.agent_manager.run(target_agent_id, message, self.run_metadata)

        if isinstance(response, CompletionResponse):
            return response.get_text()
        return str(response)

    def set_active_agent(self, agent_id: str):
        """Set the active agent by ID."""
        if agent_id not in self.agents:
            raise ValueError(f"Invalid agent ID: {agent_id}")
        self.active_agent_id = agent_id
        self.logger.info(f"Active agent set to: {agent_id}")

    def get_agent_ids(self) -> List[str]:
        """Get a list of all available agent IDs."""
        return list(self.agents.keys())

    def get_active_agent_id(self) -> str:
        """Get the current active agent ID."""
        return self.agent_manager.active_agent.id

    async def cleanup(self):
        """Clean up resources used by the client."""
        self.logger.info("Cleaning up AsyncCueClient")
        await self.agent_manager.clean_up()
