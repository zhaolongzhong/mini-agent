import os
import json
import logging
from typing import Dict, List, Union, Optional
from pathlib import Path

from pydantic import BaseModel

from .llm import LLMClient
from .tools import Tool, MemoryTool, ToolManager
from .utils import DebugUtils, record_usage
from .context import DynamicContextManager, ProjectContextManager
from .schemas import (
    Author,
    AgentConfig,
    RunMetadata,
    MessageParam,
    CompletionRequest,
    CompletionResponse,
    ConversationContext,
    ToolResponseWrapper,
    ToolCallToolUseBlock,
)
from ._agent_summarizer import ContentSummarizer
from .memory.memory_manager import DynamicMemoryManager
from .system_message_builder import SystemMessageBuilder

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: AgentConfig):
        self.id = config.id
        self.config = config
        self.tool_manager: Optional[ToolManager] = None
        self.summarizer = ContentSummarizer(AgentConfig(model="gpt-4o-mini"))
        self.memory_manager = DynamicMemoryManager(max_tokens=1000)
        self.project_context_manager = ProjectContextManager()
        self.context = DynamicContextManager(
            model=self.config.model,
            max_tokens=12000 if self.config.is_primary else 4096,
            summarizer=self.summarizer,
        )
        self.client: LLMClient = LLMClient(self.config)
        self.metadata: Optional[RunMetadata] = None
        self.description = self._generate_description()
        self.other_agents_info = ""
        self.tool_json = None
        self.conversation_context: Optional[ConversationContext] = None  # current conversation context
        self.system_message_builder = SystemMessageBuilder(self.id, self.config)
        self.setup_feedback()

    def get_system_message(self) -> MessageParam:
        self.system_message_builder.set_conversation_context(self.conversation_context)
        self.system_message_builder.set_other_agents_info(self.other_agents_info)
        return self.system_message_builder.build()

    async def _get_recent_memories(self) -> Optional[dict]:
        """Should be called whenever there is a memory update"""
        if not self.config.enable_services or Tool.Memory not in self.config.tools:
            return None
        try:
            memory_tool: MemoryTool = self.tool_manager.tools[Tool.Memory.value]
            memories = await memory_tool.get_recent_memories(limit=5)
            if memories:
                memories.reverse()  # # oldest -> newest order, oldest first, FIFO when limit reached
                for memory in memories:
                    if memory.strip():
                        self.memory_manager.add_memory(memory)

                # Get formatted memories respecting token limits
                return self.memory_manager.get_formatted_memories()

        except Exception as e:
            logger.error(f"Ran into {e} while trying to get recent memories.")
            return None

    def _generate_description(self) -> str:
        """Return the description about the agent."""
        description = ""
        if self.config.description:
            description = self.config.description
        if not self.config.tools:
            return
        tool_names = [tool.value for tool in self.config.tools]
        if not tool_names:
            return description
        description += f" Agent {self.id} is able to use these tools: {', '.join(tool_names)}"
        return description

    def _init_tools(self, tool_manager: ToolManager):
        if not self.tool_manager:
            self.tool_manager = tool_manager
        if not self.tool_json and self.config.tools:
            self.tool_json = self.tool_manager.get_tool_definitions(self.config.model, self.config.tools)

    async def add_message(self, message: Union[CompletionResponse, ToolResponseWrapper, MessageParam]) -> None:
        await self.add_messages([message])

    async def add_messages(self, messages: List[Union[CompletionResponse, ToolResponseWrapper, MessageParam]]) -> None:
        await self.context.add_messages(messages)

    def snapshot(self) -> str:
        """Take a snapshot of current message list and save to a file"""
        return DebugUtils.take_snapshot(self.context.messages)

    def setup_feedback(self) -> str:
        """Setup system feedback"""
        if not self.config.feedback_path:
            self.config.feedback_path = Path(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs/feedbacks"))
            )
            self.config.feedback_path.mkdir(parents=True, exist_ok=True)

    async def build_message_params(self) -> list[dict]:
        """
        Build a list of message parameter dictionaries for the completion API call.

        The method constructs the message parameters in order from most static to least static data
        to optimize prompt caching efficiency. The construction follows this sequence:
        1. Project context (static)
        2. Relevant memories (semi-static)
        3. Summary of removed messages (if any)
        4. Current message list (dynamic)
        """
        # Get message list
        messages = self.context.get_messages()
        logger.debug(f"{self.id} run message param size: {len(messages)}")
        message_params = [
            msg.model_dump() if hasattr(msg, "model_dump") else msg.dict() if hasattr(msg, "dict") else msg
            for msg in messages
        ]
        # Get recent memories
        memories_param = await self._get_recent_memories()
        if memories_param:
            message_params.insert(0, memories_param)
            logger.debug(f"Recent memories: {json.dumps(memories_param, indent=4)}")

        # Get project context
        project_context = self.project_context_manager.load_project_context(self.config.project_context_path)
        if project_context:
            message_params.insert(0, project_context)
        return message_params

    async def run(self, tool_manager: ToolManager, author: Optional[Author] = None):
        self._init_tools(tool_manager)
        message_params = await self.build_message_params()
        return await self.send_messages(messages=message_params, author=author)

    async def send_messages(
        self,
        messages: List[Union[BaseModel, Dict]],
        metadata: Optional[RunMetadata] = None,
        author: Optional[Author] = None,
    ) -> Union[CompletionResponse, ToolCallToolUseBlock]:
        if not self.metadata:
            self.metadata = metadata

        messages_dict = [
            msg.model_dump(exclude_none=True, exclude_unset=True) if isinstance(msg, BaseModel) else msg
            for msg in messages
        ]

        completion_request = CompletionRequest(
            author=Author(name=self.id, role="assistant") if not author else author,
            model=self.config.model,
            messages=messages_dict,
            metadata=metadata,
            tool_json=self.tool_json,
            system_prompt_suffix=self.get_system_message().content,
        )
        response = await self.client.send_completion_request(completion_request)
        record_usage(response)
        logger.debug(f"{self.id} response: {response}")
        return response

    def build_context_for_next_agent(self, max_messages: int = 6) -> str:
        """
        Build context to be passed to the next agent, excluding the current transfer command and its result.

        Args:
            max_messages: Number of previous messages to include (0-12).
                        If 0, returns empty string as no history should be included.

        Returns:
            str: Formatted message history, excluding current transfer command and result
        """
        if max_messages == 0:
            return ""

        history = self.context.get_messages()

        # Since the last two messages are the transfer command and its result,
        # we exclude them and then take up to max_messages from the remaining history
        history_without_transfer = history[:-2] if len(history) >= 2 else []

        # Calculate how many messages to take
        start_idx = max(0, len(history_without_transfer) - max_messages)
        messages = history_without_transfer[start_idx:]

        messages_content = ",".join(str(msg) for msg in messages)

        return messages_content
