import copy
import logging
from typing import Callable, Dict, List, Optional, Union

from ._agent import Agent
from .schemas import AgentConfig, CompletionResponse, MessageParam, RunMetadata
from .tools._tool import Tool

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        logger.info("AgentManager initialized")
        self.agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None

    async def transfer_to_agent(self, from_agent_id: str, to_agent_id: str, message: str) -> str:
        """Transfer message list to target agent and make the target agent as active agent"""
        logger.info(f"transfer_to_agent from_agent_id: {from_agent_id}, to_agent_id: {to_agent_id}, message: {message}")
        try:
            # overwrite by using active agent id
            from_agent_id = self.active_agent.id
            from_agent = self.agents[from_agent_id]
            to_agent = self.agents[to_agent_id]
            if not to_agent:
                error_message = f"There is no agent with id: {to_agent_id}"
                logger.error(error_message)
                return error_message
            history = copy.deepcopy(from_agent.get_messages())
            messages = [*history]
            to_agent.memory.messages.clear()
            await to_agent.memory.saveList(messages)
            self.active_agent = to_agent
            logger.info(
                f"transfer_to_agent done, active agent is {self.active_agent.id}, messages: {len(self.active_agent.memory.messages)}, last message: {messages[-1]}"
            )
            return f"transfer from {from_agent_id} to {self.active_agent.id} successfully, current active agent is {self.active_agent.id} who now starts interacting with the user."
        except Exception as e:
            error_msg = f"transfer_to_agent failed due to: {e}"
            logger.error(error_msg)
            return error_msg

    def register_agent(self, config: AgentConfig) -> Agent:
        if config.id in self.agents:
            logger.warning(f"Agent with id {config.id} already exists, returning existing agent.")
            return self.agents[config.id]

        agent = Agent(config=config, agent_manager=self)
        self.agents[agent.config.id] = agent
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

    async def run(
        self,
        agent_identifier: str,
        message: str,
        run_metadata: RunMetadata = RunMetadata(),
    ) -> CompletionResponse:
        agent = self.get_agent(agent_identifier)
        if not agent:
            raise ValueError(f"Agent with identifier '{agent_identifier}' not found. Register an agent first.")

        self.active_agent = agent
        user_message = MessageParam(role="user", content=message)
        await self.active_agent.memory.save(user_message)

        response = None
        turns_count = 0
        while True:
            turns_count += 1
            if turns_count >= run_metadata.max_turns:
                logger.warning(f"Run reaches max turn: {run_metadata.max_turns}")
                break
            messages = self.active_agent.get_message_params()  # convert message params
            logger.debug(f"run_count: {turns_count}, {self.active_agent.id}, size: {len(messages)}")
            history = [
                msg.model_dump() if hasattr(msg, "model_dump") else msg.dict() if hasattr(msg, "dict") else msg
                for msg in messages
            ]
            response: CompletionResponse = await self.active_agent.send_messages(history)

            if isinstance(response, CompletionResponse):
                if response.error:
                    logger.error(response.error.model_dump())
                    # Even if there's an error, store the interaction in memory
                    # This preserves the tool call/response pair for:
                    # - Maintaining conversation context
                    # - Avoiding repeated failed attempts
                    await self.active_agent.memory.save(response)
                    continue

                await self.active_agent.memory.save(response)
                tool_calls = response.get_tool_calls()
                if not tool_calls:
                    break

                tool_result_wrapper = await self.active_agent.process_tools_with_timeout(tool_calls, 30)
                if tool_result_wrapper.tool_result_message:
                    await self.active_agent.memory.saveList([tool_result_wrapper.tool_result_message])
                elif tool_result_wrapper.tool_messages:
                    await self.active_agent.memory.saveList(tool_result_wrapper.tool_messages)
                else:
                    raise Exception(f"Unexpected response: {tool_result_wrapper}")

            else:
                raise Exception(f"Unexpected response: {response}")

        return response

    async def clean_up(self):
        self.agents.clear()
        self.active_agent = None
        logger.info("All agents cleaned up and removed.")

    def get_agent(self, identifier: str) -> Optional[Agent]:
        if identifier in self.agents:
            return self.agents[identifier]

        for agent in self.agents.values():
            if agent.config.name == identifier:
                return agent

        return None

    def set_active_agent(self, agent_id: str):
        self.active_agent = self.get_agent(agent_id)

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
