import copy
import logging
from typing import Callable, Dict, List, Optional, Union

from ._agent import Agent
from .schemas import AgentConfig, Author, CompletionResponse, MessageParam, RunMetadata, ToolResponseWrapper
from .tools._tool import Tool

logger = logging.getLogger(__name__)

chat_with_agent = "chat_with_agent"


class AgentManager:
    def __init__(self):
        logger.info("AgentManager initialized")
        self.agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None
        self.new_active_agent: Optional[Agent] = None

    async def chat_with_agent(self, from_agent_id: str, to_agent_id: str, message: str) -> str:
        """Chat with another agent"""
        logger.debug(f"chat_with_agent from_agent_id: {from_agent_id}, to_agent_id: {to_agent_id}, message: {message}")
        try:
            from_agent = self.agents[from_agent_id]
            to_agent = self.agents[to_agent_id]
            if not to_agent:
                error_message = f"There is no agent with id: {to_agent_id}"
                logger.error(error_message)
                return error_message
            history = copy.deepcopy(from_agent.get_messages())
            self.new_active_agent = to_agent
            tool_result_message = f"<system_context>{from_agent_id} sends message to {self.new_active_agent.id} successfully, {self.new_active_agent.id} is active agent.</system_context>"
            # remove the transfer tool call and append message from calling agent
            # in this way, we keep the conversation cohensive with less noise
            max_messages = 15
            start_idx = max(0, len(history) - (max_messages + 1))  # -11 to account for the -1 later
            messages = history[start_idx:-1]
            messages_content = ",".join([str(msg) for msg in messages])

            messages_content = ",".join([str(msg) for msg in messages])
            history = MessageParam(
                role="assistant",
                content=f"This is some context from conversation between agent {from_agent_id} and other agents: <background>{messages_content}</background> \n\nThe following message is from {from_agent_id} to {to_agent_id}",
            )
            from_agent_message = MessageParam(role="assistant", content=message, name=from_agent.config.name)
            messages.append(from_agent_message)
            messages = [history, from_agent_message]
            to_agent.memory.messages.clear()
            await to_agent.memory.saveList(messages)

            logger.info(
                f"transfer_to_agent done, new active agent will be {self.new_active_agent.id}, messages: {len(self.new_active_agent.memory.messages)}"
            )
            return tool_result_message
        except Exception as e:
            error_msg = f"chat_with_agent failed due to: {e}"
            logger.error(error_msg)
            return error_msg

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

        author = Author(role="user", name="")
        while True:
            if self.new_active_agent:
                self.active_agent = self.new_active_agent
                self.new_active_agent = None
            turns_count += 1
            if not self.should_continue_run(turns_count, run_metadata):
                break

            response: CompletionResponse = await self.active_agent.run(author)
            author = None

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

                tool_result_wrapper = await self.active_agent.process_tools_with_timeout(
                    tool_calls=tool_calls, timeout=30, author=response.author
                )
                if isinstance(tool_result_wrapper, ToolResponseWrapper):
                    await self.active_agent.memory.save(tool_result_wrapper)
                else:
                    raise Exception(f"Unexpected response: {tool_result_wrapper}")

            else:
                raise Exception(f"Unexpected response: {response}")

        return response

    def should_continue_run(self, turns_count: int, run_metadata: RunMetadata):
        """
        Determines if the game loop should continue based on turn count and user input.

        Args:
            turns_count: Current number of turns
            run_metadata: Metadata containing max turns and debug settings

        Returns:
            bool: True if the loop should continue, False otherwise
        """
        if run_metadata.enable_turn_debug:
            response = input(
                f"Maximum turn {run_metadata.max_turns}, current: {turns_count}. Debug. Continue? (y/n, press Enter to continue): "
            )
            if response.lower() not in ["y", "yes", ""]:
                logger.warning("Stopped by user.")
                return False
        if turns_count >= run_metadata.max_turns:
            logger.warning(f"Run reaches max turn: {run_metadata.max_turns}")
            response = input(
                f"Maximum turn {run_metadata.max_turns} reached. Continue? (y/n, press Enter to continue): "
            )
            if response.lower() not in ["y", "yes", ""]:
                logger.warning("Stopped by user.")
                return False

        return True

    async def clean_up(self):
        self.agents.clear()
        self.active_agent = None
        logger.info("All agents cleaned up and removed.")

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
            logger.debug(f"Added tool {tool} to agent {agent_id}")

    def list_agents(self, exclude: List[str] = []) -> List[dict[str, str]]:
        return [
            {"id": agent.id, "name": agent.config.name, "description": agent.description}
            for agent in self.agents.values()
            if agent.id not in exclude
        ]
