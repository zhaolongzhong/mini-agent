import copy
import json
import asyncio
import logging
from typing import Dict, List, Union, Callable, Optional

from pydantic import BaseModel
from anthropic.types import ToolUseBlock
from openai.types.chat import (
    ChatCompletionMessageToolCall as ToolCall,
    ChatCompletionToolMessageParam as ToolMessageParam,
)
from anthropic.types.beta import BetaMessageParam, BetaTextBlockParam, BetaImageBlockParam, BetaToolResultBlockParam

from .llm import LLMClient
from .tools import Tool, ToolResult, ToolManager
from .utils import record_usage
from .schemas import (
    Author,
    AgentConfig,
    RunMetadata,
    MessageParam,
    CompletionRequest,
    AgentHandoffResult,
    CompletionResponse,
    ConversationContext,
    ToolResponseWrapper,
    ToolCallToolUseBlock,
)
from .memory.memory import InMemoryStorage

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: AgentConfig, agent_manager: "AgentManager"):  # type: ignore # noqa: F821
        self.id = config.id.strip().replace(" ", "_")
        self.config = config
        self.tool_manager = ToolManager()
        self.memory = InMemoryStorage()
        self.client: LLMClient = LLMClient(self.config)
        self.metadata: Optional[RunMetadata] = None
        self.agent_manager = agent_manager
        self.description = self._generate_description()
        self.other_agents_info = ""
        self.tool_json = None
        self.conversation_context: Optional[ConversationContext] = None  # current conversation context

    def get_system_message(self) -> MessageParam:
        instruction = ""
        if self.config.instruction:
            instruction = f"\n* {self.config.instruction}{instruction}"
        if self.config.is_primary:
            instruction += f"""
You are {self.id}, a primary agent in a multi-agent system. Please follow these core rules:

1. To communicate with other agents:
   - Use the `chat_with_agent` tool
   - Specify the target agent's ID
   - System automatically includes last 3 messages as context
   - Provide additional context if the recent messages alone are insufficient

2. All responses not using `chat_with_agent` will be sent directly to the user, so please format them accordingly
"""
        if self.other_agents_info:
            instruction += f"\n* You are aware of the following other agents:\n{self.other_agents_info}"
        if not self.config.is_primary and self.conversation_context:
            instruction += f"\n* Current participants in this conversation are:\n{','.join(self.conversation_context.participants)}"

        return MessageParam(role="system", name=self.id, content=f"<IMPORTANT>{instruction}</IMPORTANT>")

    def get_messages(self) -> List:
        """Retrieve the original list of messages from the Pydantic model."""
        return self.memory.messages

    def get_message_params(self) -> List[Dict]:
        """Retrieve a list of message parameter dictionaries for the completion API call."""
        return self.memory.get_message_params(self.config.model)

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

    def add_tool_to_agent(self, tool: Union[Callable, Tool]) -> None:
        self.config.tools.append(tool)
        logger.debug(f"Added tool {tool} to agent {self.config.id}")

    async def chat_with_agent(self, to_agent_id: str, message: str) -> AgentHandoffResult:
        """Chat with another agent"""
        messages = self.build_next_agent_context(to_agent_id, message)
        return AgentHandoffResult(
            from_agent_id=self.id,
            to_agent_id=to_agent_id,
            context=messages,
            message=message,
        )

    async def run(self, author: Optional[Author] = None):
        if not self.tool_json and self.config.tools:
            # chat_with_agent is added later so we cannot initialize in init
            self.tool_json = self.tool_manager.get_tool_definitions(self.config.model, self.config.tools)
        messages = self.get_message_params()  # convert message params
        logger.debug(f"{self.id}, size: {len(messages)}")
        history = [
            msg.model_dump() if hasattr(msg, "model_dump") else msg.dict() if hasattr(msg, "dict") else msg
            for msg in messages
        ]
        return await self.send_messages(messages=history, author=author)

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
        return response

    async def process_tools_with_timeout(
        self,
        tool_calls: List[ToolCallToolUseBlock],
        timeout: int = 30,
        author: Optional[Author] = None,
    ) -> ToolResponseWrapper:
        tool_results = []
        tasks = []

        for tool_call in tool_calls:
            if isinstance(tool_call, ToolCall):
                tool_name = tool_call.function.name
                tool_id = tool_call.id
                kwargs = json.loads(tool_call.function.arguments)
            elif isinstance(tool_call, ToolUseBlock):
                tool_name = tool_call.name
                tool_id = tool_call.id
                kwargs = tool_call.input
            else:
                raise ValueError(f"Unsupported tool call type: {type(tool_call)}")

            chat_with_agent = "chat_with_agent"
            if tool_name not in self.tool_manager.tools and tool_name not in chat_with_agent:
                error_message = f"Tool '{tool_name}' not found. {self.tool_manager.tools.keys()}"
                logger.error(f"{error_message}, tool_call: {tool_call}")
                tool_results.append(self.create_error_response(tool_id, tool_name, error_message))
                continue

            if tool_name == chat_with_agent:
                handoff_result = await self.chat_with_agent(**kwargs)
                return ToolResponseWrapper(agent_handoff_result=handoff_result)

            tool_func = self.tool_manager.tools[tool_name]
            task = asyncio.create_task(self.run_tool(tool_func, **kwargs))
            tasks.append((task, tool_id, tool_name))

        base64_images = []
        for task, tool_id, tool_name in tasks:
            try:
                tool_result = await asyncio.wait_for(task, timeout=timeout)
                base64_image = tool_result.base64_image
                if base64_image:
                    base64_images.append(base64_image)
                tool_results.append(self.create_success_response(tool_id, tool_result, tool_name))
            except asyncio.TimeoutError:
                error_message = f"Timeout while calling tool <{tool_name}> after {timeout}s."
                tool_results.append(self.create_error_response(tool_id, error_message, tool_name))
            except Exception as e:
                error_message = f"Error while calling tool <{tool_name}>: {e}"
                tool_results.append(self.create_error_response(tool_id, error_message, tool_name))

        response = None
        if "claude" in self.config.model:
            tool_result_message = BetaMessageParam(role="user", content=tool_results)
            response = ToolResponseWrapper(tool_result_message=tool_result_message, author=author)
        else:
            response = ToolResponseWrapper(tool_messages=tool_results, author=author, base64_images=base64_images)

        return response

    async def run_tool(self, tool_func, **kwargs):
        return await tool_func(**kwargs)

    def create_success_response(self, tool_id: str, result: ToolResult, tool_name: Optional[str] = None):
        if "claude" in self.config.model:
            tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
            is_error = False
            if result.error:
                is_error = True
                tool_result_content = _maybe_prepend_system_tool_result(result, result.error)
            else:
                if result.output:
                    tool_result_content.append(
                        {
                            "type": "text",
                            "text": _maybe_prepend_system_tool_result(result, result.output),
                        }
                    )
                if result.base64_image:
                    tool_result_content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": result.base64_image,
                            },
                        }
                    )

            return BetaToolResultBlockParam(
                tool_use_id=tool_id, content=tool_result_content, type="tool_result", is_error=is_error
            )
        else:
            tool_result_content = ""
            if result.error:
                is_error = True
                tool_result_content = _maybe_prepend_system_tool_result(result, result.error)
            else:
                if result.output:
                    tool_result_content = _maybe_prepend_system_tool_result(result, result.output)
                # if result.base64_image:
                #     # handle in loop
                #     pass

            return ToolMessageParam(tool_call_id=tool_id, name=tool_name, role="tool", content=tool_result_content)

    def create_error_response(self, tool_id: str, tool_name: str, error_message: str):
        if "claude" in self.config.model:
            result_param = BetaToolResultBlockParam(
                tool_use_id=tool_id, content=error_message, type="tool_result", is_error=True
            )
            return result_param
        else:
            return ToolMessageParam(tool_call_id=tool_id, name=tool_name, role="tool", content=error_message)

    def build_next_agent_context(self, to_agent: str, last_message: str) -> List[Dict]:
        history = copy.deepcopy(self.get_messages())
        # remove the transfer tool call and append message from calling agent
        # in this way, we keep the conversation cohensive with less noise
        max_messages = 6
        start_idx = max(0, len(history) - (max_messages + 1))
        messages = history[start_idx:-1]
        messages_content = ",".join([str(msg) for msg in messages])

        messages_content = ",".join([str(msg) for msg in messages])
        history = MessageParam(
            role="assistant",
            content=f"This is context from agent {self.id}: <background>{messages_content}</background> \n\nThe following message is from {self.id} to {to_agent}",
        )
        from_agent_message = MessageParam(role="assistant", content=last_message, name=self.id)
        messages.append(from_agent_message)
        messages = [history, from_agent_message]
        return messages


def _maybe_prepend_system_tool_result(result: ToolResult, result_text: str):
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text
