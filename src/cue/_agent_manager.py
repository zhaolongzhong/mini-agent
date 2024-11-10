import asyncio
import logging
from typing import Any, Dict, List, Callable, Optional

from .utils import DebugUtils, console_utils
from ._agent import Agent
from .schemas import (
    Author,
    AgentConfig,
    RunMetadata,
    MessageParam,
    AgentTransfer,
    CompletionResponse,
    ConversationContext,
    ToolResponseWrapper,
)
from .services import ServiceManager
from .tools._tool import ToolManager
from .schemas.event_message import (
    EventMessage,
    ClientMessage,
    EventMessageType,
    PromptEventPayload,
)

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(
        self,
        prompt_callback=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        mode: str = "cli",
    ):
        logger.info("AgentManager initialized")
        self.prompt_callback = prompt_callback
        self.loop = loop or asyncio.get_event_loop()
        self.mode = mode
        self._agents: Dict[str, Agent] = {}
        self.active_agent: Optional[Agent] = None
        self.primary_agent: Optional[Agent] = None
        self.service_manager: Optional[ServiceManager] = None
        self.tool_manager: Optional[ToolManager] = None
        self.run_metadata: Optional[RunMetadata] = None
        self.console_utils = console_utils
        # Removed MessageQueueManager
        self.user_message_queue: asyncio.Queue[str] = asyncio.Queue()
        # Reference to the execute_run task
        self.execute_run_task: Optional[asyncio.Task] = None
        # Event to signal stopping the run
        self.stop_run_event: asyncio.Event = asyncio.Event()

    async def initialize(self, enable_services: Optional[bool] = False):
        logger.debug("initialize")
        if enable_services or self.mode in ["runner", "client"]:
            self.service_manager = await ServiceManager.create(on_message=self.handle_message)
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
        self.run_metadata = RunMetadata()

        if self.service_manager:
            try:
                await self.service_manager.assistants.create_default_assistant()
            except Exception as e:
                logger.error(f"Error setting up memory service: {e}")

        if not self.tool_manager:
            memory_client = self.service_manager.memories if self.service_manager else None
            self.tool_manager = ToolManager(memory_client)

    async def run(
        self,
        active_agent_id: str,
        message: str,
        run_metadata: RunMetadata = RunMetadata(),
        callback: Optional[Callable[[CompletionResponse], Any]] = None,
    ) -> None:
        """Queue a message for processing with optional callback."""
        if run_metadata:
            self.run_metadata = run_metadata
        self.active_agent = self._agents[active_agent_id]
        # Directly add message to the agent's message history
        if message:
            user_message = MessageParam(role="user", content=message)
            self.active_agent.add_message(user_message)
        # Log the message
        logger.debug(f"Queued message for agent {active_agent_id}: {message}")

        # Start execute_run if not already running
        if not self.execute_run_task or self.execute_run_task.done():
            self.execute_run_task = asyncio.create_task(self._execute_run(callback))
            logger.debug("Started execute_run_task.")

    async def _execute_run(
        self,
        callback: Optional[Callable[[CompletionResponse], Any]] = None,
    ):
        """Main loop to process messages from the active agent."""
        logger.debug("execute_run loop started.")
        response = None
        turns_count = 0

        author = Author(role="user", name="")
        while True:
            # Check if a stop signal has been received
            if self.stop_run_event.is_set():
                logger.info("Stop signal received. Exiting execute_run loop.")
                break

            # Check for dynamically injected user messages
            while not self.user_message_queue.empty():
                try:
                    new_message = self.user_message_queue.get_nowait()
                    logger.debug(f"Received new user message during run: {new_message}")
                    # Process the new message immediately
                    new_user_message = MessageParam(role="user", content=new_message)
                    self.active_agent.add_message(new_user_message)
                except asyncio.QueueEmpty:
                    break

            turns_count += 1
            if not await self.should_continue_run(turns_count, self.run_metadata):
                break

            try:
                response: CompletionResponse = await self.active_agent.run(author)
            except asyncio.CancelledError:
                logger.info("execute_run task was cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error during agent run: {e}")
                break

            await callback(response)
            await self.broadcast_response(response)

            author = Author(role="assistant", name="")
            if not isinstance(response, CompletionResponse):
                if response.error:
                    logger.error(response.error.model_dump())
                    # Even if there's an error, store the interaction in memory
                    self.active_agent.add_message(response)
                    continue
                else:
                    raise Exception(f"Unexpected response: {response}")

            tool_calls = response.get_tool_calls()
            if not tool_calls:
                self.active_agent.add_message(response)
                if self.active_agent.config.is_primary:
                    DebugUtils.log_chat({"assistant": response.get_text()})
                    return response
                else:
                    logger.info("Auto switch to primary agent")
                    transfer = AgentTransfer(to_agent_id=self.primary_agent.id, message=response.get_text())
                    await self._handle_transfer(transfer)
                    continue

            text_content = response.get_text()
            if text_content:
                DebugUtils.log_chat({"assistant": text_content})

            tool_result = await self.active_agent.process_tools_with_timeout(
                tool_calls=tool_calls, timeout=30, author=response.author
            )
            if isinstance(tool_result, ToolResponseWrapper):
                # Add tool use and tool result pair
                self.active_agent.add_message(response)
                self.active_agent.add_message(tool_result)
                if tool_result.agent_transfer:
                    transfer = tool_result.agent_transfer
                    await self._handle_transfer(transfer)
                    # Pick up new active agent in next loop
                    continue
                else:
                    if tool_result.base64_images:
                        logger.debug("Add base64_image result to message params")
                        tool_result_content = {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{tool_result.base64_images[0]}"},
                        }

                        contents = [
                            {"type": "text", "text": "Please check previous query info related to this image"},
                            tool_result_content,
                        ]
                        # ChatCompletionUserMessageParam
                        message_param = {"role": "user", "content": contents}
                        self.active_agent.add_message(message_param)
            else:
                raise Exception(f"Unexpected response: {tool_result}")

        logger.info("Exiting execute_run loop.")
        return response

    async def _handle_transfer(self, agent_transfer: AgentTransfer) -> None:
        """Process agent transfer by updating active agent and transferring context.

        Args:
            agent_transfer: Contains target agent ID and context to transfer

        The method clears previous memory and transfers either single or list context
        to the new active agent.
        """
        if agent_transfer.to_agent_id not in self._agents:
            available_agents = ", ".join(self._agents.keys())
            error_msg = f"Target agent '{agent_transfer.to_agent_id}' not found. Available agents: {available_agents}"
            self.active_agent.add_message(MessageParam(role="user", content=error_msg))
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
        for msg in messages:
            self.active_agent.add_message(msg)
        self.active_agent.conversation_context = ConversationContext(
            participants=[from_agent_id, agent_transfer.to_agent_id]
        )

    async def should_continue_run(self, turns_count: int, run_metadata: RunMetadata) -> bool:
        """
        Determines if the game loop should continue based on turn count and user input.

        Args:
            turns_count: Current number of turns
            run_metadata: Metadata containing max turns and debug settings

        Returns:
            bool: True if the loop should continue, False otherwise
        """
        if run_metadata.enable_turn_debug:
            user_response = await self.prompt_callback(
                f"Maximum turn {run_metadata.max_turns}, current: {turns_count}. Debug. Continue? (y/n, press Enter to continue): "
            )
            if user_response.lower() not in ["y", "yes", ""]:
                logger.warning("Stopped by user.")
                return False

        if turns_count >= run_metadata.max_turns:
            if self.active_agent.config.is_test:
                return False
            logger.warning(f"Run reaches max turn: {run_metadata.max_turns}")
            run_metadata.max_turns += 10  # Dynamically increase max turns
            user_response = await self.prompt_callback(
                f"Increase maximum turn to {run_metadata.max_turns}, continue? (y/n, press Enter to continue): "
            )
            if user_response.lower() not in ["y", "yes", ""]:
                logger.warning("Stopped by user.")
                return False

        return True

    async def broadcast_response(self, completion_response: CompletionResponse):
        logger.debug("broadcast_response")
        if not self.service_manager:
            return

        msg = EventMessage(
            type=EventMessageType.ASSISTANT,
            payload=ClientMessage(role="assistant", content=completion_response.get_text(), name=self.active_agent.id),
        )
        await self.service_manager.broadcast(msg.model_dump_json())

    async def broadcast_user_message(self, user_input: str) -> None:
        """Broadcast user message through websocket"""
        logger.debug(f"broadcast user message: {user_input}")
        msg = EventMessage(type=EventMessageType.PROMPT, payload=PromptEventPayload(role="user", content=user_input))
        await self.service_manager.broadcast(msg.model_dump_json())

    async def handle_message(self, event: EventMessage) -> None:
        """Receive user message from websocket"""
        logger.debug(f"Handling message: {event.model_dump_json(indent=4)}")
        if event.type == EventMessageType.PROMPT and event.client_id != self.service_manager.client_id:
            if isinstance(event.payload, PromptEventPayload):
                user_message = event.payload.content
                self.console_utils.print_msg("User", user_message)
                if not self.run_metadata:
                    self.run_metadata = RunMetadata()
                if self.execute_run_task and not self.execute_run_task.done():
                    # Inject the message dynamically
                    await self.inject_user_message(user_message)
                    logger.debug("handle_message - User message injected dynamically.")
                else:
                    # Start a new run
                    logger.debug("handle_message - User message queued for processing.")
                    await self.run(self.active_agent.id, user_message, self.run_metadata, callback=self.handle_response)
        elif event.type == EventMessageType.ASSISTANT and event.client_id != self.service_manager.client_id:
            if isinstance(event.payload, PromptEventPayload):
                message = event.payload.content
                name = event.payload.name if event.payload.name else "Assistant"
                self.console_utils.print_msg(name, message)

    async def handle_response(self, response: CompletionResponse):
        self.console_utils.print_msg(self.active_agent.id, f"{response.get_text()}")

    async def inject_user_message(self, user_input: str) -> None:
        """Inject a user message into the ongoing run."""
        logger.debug(f"Injecting user message: {user_input}")
        await self.user_message_queue.put(user_input)

    def register_agent(self, config: AgentConfig) -> Agent:
        if config.id in self._agents:
            logger.warning(f"Agent with id {config.id} already exists, returning existing agent.")
            return self._agents[config.id]

        agent = Agent(config=config, agent_manager=self)
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
                # todo: handle unfinish tool result, check last message if it's tool, then append tool result
        else:
            logger.info("No active run to stop.")
