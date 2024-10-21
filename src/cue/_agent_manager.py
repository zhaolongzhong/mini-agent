import copy
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from ._agent import Agent
from .schemas import AgentConfig, CompletionResponse, UserMessage
from .tools._tool import Tool

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        logger.info("AgentManager initialized")
        self.agents: Dict[str, Agent] = {}
        self.main_agent: Optional[Agent] = None

    async def call_agent(self, from_agent_id: str, to_agent_id: str, message: str) -> Any:
        """Call an agent with the given ID."""
        logger.debug(f"call_agent from_agent_id: {from_agent_id}, to_agent_id: {to_agent_id}, message: {message}")

        try:
            from_agent = self.agents[from_agent_id]
            to_agent = self.agents[to_agent_id]
            if not to_agent:
                error_message = f"There is no agent with id: {to_agent_id}"
                logger.error(error_message)
                return error_message
            history = copy.deepcopy(from_agent.get_messages())
            # remove last tool call message which is call_agent
            history.pop()

            messages = [
                to_agent.get_system_message(),
                *history,
                {"role": "assistant", "name": from_agent.config.name, "content": message},
            ]

            response = await to_agent.send_messages(messages)
            result = {"role": "assistant", "name": to_agent.config.name, "content": response.get_text()}
            return result
        except Exception as e:
            logger.error(f"Error when calling {to_agent_id}. Error: \n{e}")
            return f"Error when calling {to_agent_id}"

    def register_agent(self, config: AgentConfig) -> Agent:
        if config.id in self.agents:
            logger.warning(f"Agent with id {config.id} already exists, returning existing agent.")
            return self.agents[config.id]

        agent = Agent(config=config, agent_manager=self)
        self.agents[agent.config.id] = agent
        self.main_agent = agent
        logger.info(
            f"register_agent {agent.config.id} (name: {config.name}), available agents: {list(self.agents.keys())}"
        )
        self.update_other_agents_info()
        return agent

    def update_other_agents_info(self):
        for agent_id, agent in self.agents.items():
            other_agents_info = self.list_agents(exclude=[agent_id])
            agent.other_agents_info = other_agents_info
            logger.debug(f"{agent_id} other_agents_info: {other_agents_info}")

    async def run(self, agent_identifier: str, message: str) -> CompletionResponse:
        agent = self.get_agent(agent_identifier)
        if not agent:
            raise ValueError(f"Agent with identifier '{agent_identifier}' not found. Register an agent first.")

        self.main_agent = agent
        user_message = UserMessage(role="user", content=message)
        await self.main_agent.memory.save(user_message)

        # Prepare messages list and append latest user message
        messages = self.main_agent.get_messages()
        history = copy.deepcopy(messages)
        history.append(user_message)
        return await self.main_agent.send_messages(history)

    async def clean_up(self):
        self.agents.clear()
        self.main_agent = None
        logger.info("All agents cleaned up and removed.")

    def get_agent(self, identifier: str) -> Optional[Agent]:
        if identifier in self.agents:
            return self.agents[identifier]

        for agent in self.agents.values():
            if agent.config.name == identifier:
                return agent

        return None

    def add_tool_to_agent(self, agent_id: str, tool: Union[Callable, Tool]) -> None:
        if agent_id in self.agents:
            self.agents[agent_id].config.tools.append(tool)
            logger.info(f"Added tool {tool} to agent {agent_id}")

    def list_agents(self, exclude: List[str] = []) -> List[dict[str, str]]:
        return [
            {"id": agent.id, "name": agent.config.name, "description": agent.description}
            for agent in self.agents.values()
            if agent.id not in exclude
        ]
