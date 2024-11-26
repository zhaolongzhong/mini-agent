import asyncio
import logging
from typing import Any, Dict, List, Union, Callable, Optional

from .utils import DebugUtils, console_utils
from ._agent import Agent
from .schemas import (
    AgentConfig,
    RunMetadata,
    MessageParam,
    AgentTransfer,
    CompletionResponse,
    ConversationContext,
)
from .services import ServiceManager
from ._agent_loop import AgentLoop
from .tools._tool import ToolManager
from .schemas.feature_flag import FeatureFlag
from .schemas.event_message import (
    EventMessage,
    MessagePayload,
    EventMessageType,
)

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(
        self,
        prompt_callback=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        logger.info("AgentManager initialized")
        self.prompt_callback = prompt_callback
        self.loop = loop or asyncio.get_event_loop()
        self.agent_loop = AgentLoop()
        self._agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None
        self.primary_agent: Optional[Agent] = None
        self.service_manager: Optional[ServiceManager] = None
        self.tool_manager: Optional[ToolManager] = None
        self.run_metadata: Optional[RunMetadata] = None
        self.console_utils = console_utils
        self.user_message_queue: asyncio.Queue[str] = asyncio.Queue()
        self.execute_run_task: Optional[asyncio.Task] = None
        self.stop_run_event: asyncio.Event = asyncio.Event()

    async def initialize(self, run_metadata: Optional[RunMetadata] = RunMetadata()):
        logger.debug(f"initialize mode: {run_metadata.mode}")
        self.run_metadata = run_metadata
        if self.primary_agent:
            feature_flag = self.primary_agent.config.feature_flag
        else:
            feature_flag = FeatureFlag()

        if feature_flag.enable_services or run_metadata.mode in "client":
            self.service_manager = await ServiceManager.create(
                run_metadata=self.run_metadata,
                feature_flag=feature_flag,
                on_message_received=self.on_message_received,
                agent=self.primary_agent.config,
            )
            await self.service_manager.connect()

        # Update other agents info once we set primary agent
        self._update_other_agents_info()
        await self.initialize_run()

    async def clean_up(self):
        if self.service_manager:
            await self.service_manager.close()

        cleanup_tasks = []
        for agent_id in list(self._agents.keys()):
            try:
                if hasattr(self._agents[agent_id], "cleanup"):
                    cleanup_tasks.append(asyncio.create_task(self._agents[agent_id].cleanup()))
            except Exception as e:
                logger.error(f"Error cleaning up agent {agent_id}: {e}")

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._agents.clear()
        logger.info("All agents cleaned up and removed.")

    async def initialize_run(self):
        if not self.tool_manager:
            memory_client = self.service_manager.memories if self.service_manager else None
            self.tool_manager = ToolManager(memory_client)

    async def start_run(
        self,
        active_agent_id: str,
        message: str,
        run_metadata: RunMetadata,
        callback: Optional[Callable[[CompletionResponse], Any]] = None,
    ) -> Optional[CompletionResponse]:
        """Queue a message for processing with optional callback."""
        if run_metadata:
            self.run_metadata = run_metadata
        self.active_agent = self._agents[active_agent_id]
        self.active_agent.set_service_manager(self.service_manager)
        # Start execute_run if not already running
        if not callback:
            callback = self.handle_response
        # Directly add message to the agent's message history
        if message:
            user_message = MessageParam(role="user", content=message, model=self.active_agent.config.model)
            message = await self.active_agent.add_message(user_message)
            await callback(message)
        logger.debug(f"run - queued message for agent {active_agent_id}: {message}")

        if self.run_metadata.mode == "runner":
            # in runner mode, it should be called once
            if not self.execute_run_task or self.execute_run_task.done():
                self.execute_run_task = asyncio.create_task(self._execute_run(callback))
            return
        # if in cli or test mode, return final response to the end "user"
        return await self._execute_run(callback)

    async def _execute_run(
        self,
        callback: Optional[Callable[[CompletionResponse], Any]] = None,
    ) -> Optional[CompletionResponse]:
        """
        Main execution loop for handling agent tasks and transfers between agents.

        This method orchestrates the agent execution flow, allowing agents to:
        1. Execute their primary task
        2. Process tool calls and their results
        3. Transfer control to other agents when needed

        The loop continues running as long as:
        - An agent transfer occurs (switching to a new active agent)

        The loop terminates and returns the final response when:
        - The active agent completes its task (no more tool calls)
        - An error occurs
        - A stop signal is received

        Args:
            callback: Optional function to process agent responses during execution

        Returns:
            CompletionResponse: The final response from the last active agent
        """
        logger.debug(f"execute_run loop started. run_metadata: {self.run_metadata.model_dump_json(indent=4)}")
        try:
            while True:
                response = await self.agent_loop.run(
                    agent=self.active_agent,
                    run_metadata=self.run_metadata,
                    callback=callback,
                    prompt_callback=self.prompt_callback,
                    tool_manager=self.tool_manager,
                )
                if isinstance(response, AgentTransfer):
                    if response.run_metadata:
                        logger.debug(
                            f"handle tansfer to {response.to_agent_id}, run metadata: {self.run_metadata.model_dump_json(indent=4)}"
                        )
                    await self._handle_transfer(response)
                    continue
                return response
        except Exception as e:
            logger.error(f"Ran into error for agent loop: {e}")

    async def stop_run(self):
        """Signal the execute_run loop to stop gracefully."""
        if self.execute_run_task and not self.execute_run_task.done():
            logger.info("Stopping the ongoing run...")
            self.stop_run_event.set()
            try:
                await self.execute_run_task
            except asyncio.CancelledError:
                logger.info("execute_run_task was cancelled.")
            finally:
                self.execute_run_task = None
                self.stop_run_event.clear()
                logger.info("Run has been stopped.")
        else:
            logger.info("No active run to stop.")

    async def _handle_transfer(self, agent_transfer: AgentTransfer) -> None:
        """Process agent transfer by updating active agent and transferring context.

        Args:
            agent_transfer: Contains target agent ID and context to transfer

        The method clears previous memory and transfers either single or list context
        to the new active agent.
        """
        if agent_transfer.transfer_to_primary:
            agent_transfer.to_agent_id = self.primary_agent.id

        if agent_transfer.to_agent_id not in self._agents:
            available_agents = ", ".join(self._agents.keys())
            error_msg = f"Target agent '{agent_transfer.to_agent_id}' not found. Transfer to primary: {agent_transfer.transfer_to_primary}. Available agents: {available_agents}"
            await self.active_agent.add_message(MessageParam(role="user", content=error_msg))
            logger.error(error_msg)
            return

        messages = []
        from_agent_id = self.active_agent.id
        agent_transfer.context = self.active_agent.build_context_for_next_agent(
            max_messages=agent_transfer.max_messages
        )

        if agent_transfer.context:
            context_message = MessageParam(
                role="assistant",
                content=f"Here is context from {from_agent_id} <background>{agent_transfer.context}</background>",
            )
            messages.append(context_message)

        transfer_message = MessageParam(role="assistant", content=agent_transfer.message, name=from_agent_id)
        messages.append(transfer_message)

        self.active_agent = self._agents[agent_transfer.to_agent_id]
        await self.active_agent.add_messages(messages)
        DebugUtils.take_snapshot(
            messages=messages,
            suffix=f"transfer_to_{self.active_agent.id}_{self.active_agent.config.model}",
            with_timestamp=True,
            subfolder="transfer",
        )
        self.active_agent.conversation_context = ConversationContext(
            participants=[from_agent_id, agent_transfer.to_agent_id]
        )

    async def broadcast_response(self, completion_response: CompletionResponse):
        logger.debug("broadcast assistant message")
        if not self.service_manager:
            return
        await self.service_manager.send_message_to_user(completion_response)

    async def broadcast_user_message(self, user_input: str) -> None:
        """Broadcast user message through websocket"""
        if not self.service_manager:
            logger.debug("services is not enabled")
        logger.debug(f"broadcast user message: {user_input}")
        await self.service_manager.send_message_to_assistant(user_input)

    async def on_message_received(self, event: EventMessage) -> None:
        """Receive message from websocket"""
        current_client_id = self.service_manager.client_id
        if event.type == EventMessageType.USER and event.client_id != current_client_id:
            # Anthropic uses "user" role for tool result.
            # We only use USER type only when the user sends the message directly, not tool result message
            if isinstance(event.payload, MessagePayload):
                user_message = event.payload.message
                self.console_utils.print_msg(user_message, "user")
                if self.execute_run_task and not self.execute_run_task.done():
                    # Inject the message dynamically
                    await self.inject_user_message(user_message)
                    logger.debug("handle_message - User message injected dynamically.")
                else:
                    # Start a new run
                    logger.debug("handle_message - User message queued for processing.")
                    self.run_metadata.user_messages.append(user_message)
                    await self.start_run(
                        self.active_agent.id, user_message, self.run_metadata, callback=self.handle_response
                    )
            else:
                logger.debug(f"Receive unexpected event: {event}")
        elif event.type == EventMessageType.ASSISTANT and event.client_id != current_client_id:
            logger.debug(f"handle_message receive assistant message: {event.model_dump_json(indent=4)}")
            if isinstance(event.payload, MessagePayload):
                message = event.payload.message
                self.console_utils.print_msg(message)
        else:
            logger.debug(
                f"Skip handle_message current_client_id {current_client_id}: {event.model_dump_json(indent=4)}"
            )

    async def handle_response(self, response: Union[CompletionResponse, MessageParam]):
        self.console_utils.print_msg(f"{response.get_text()}")
        await self.broadcast_response(response)

    async def inject_user_message(self, user_input: str) -> None:
        """Inject a user message into the ongoing run."""
        logger.debug(f"Injecting user message: {user_input}")
        await self.user_message_queue.put(user_input)

    def register_agent(self, config: AgentConfig) -> Agent:
        if config.id in self._agents:
            logger.warning(f"Agent with id {config.id} already exists, returning existing agent.")
            return self._agents[config.id]

        agent = Agent(config=config)
        self._agents[agent.config.id] = agent
        logger.info(
            f"register_agent {agent.config.id} (name: {config.id}), tool: {config.tools} available agents: {list(self._agents.keys())}"
        )
        if config.is_primary:
            self.primary_agent = agent
        return agent

    def _update_other_agents_info(self):
        if not self.primary_agent:
            for agent in self._agents.values():
                if agent.config.is_primary:
                    self.primary_agent = agent

        for agent_id, agent in self._agents.items():
            if agent.config.is_primary:
                agent.other_agents_info = self.list_agents(exclude=[agent_id])
            else:
                agent.other_agents_info = {
                    "id": self.primary_agent.id,
                    "description": self.primary_agent.description,
                }
            logger.debug(f"{agent_id} other_agents_info: {agent.other_agents_info}")

    def get_agent(self, identifier: str) -> Optional[Agent]:
        if identifier in self._agents:
            return self._agents[identifier]

        for agent in self._agents.values():
            if agent.config.id == identifier:
                return agent

        raise Exception(f"Agent '{identifier}' not found")

    def list_agents(self, exclude: List[str] = []) -> List[dict[str, str]]:
        return [
            {"id": agent.id, "description": agent.description}
            for agent in self._agents.values()
            if agent.id not in exclude
        ]
