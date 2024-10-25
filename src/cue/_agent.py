import asyncio
import copy
import json
import logging
from typing import Callable, Dict, List, Optional, Union

from anthropic.types import ToolUseBlock
from openai.types.chat import ChatCompletionMessageToolCall as ToolCall
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from .llm.llm_client import LLMClient
from .memory.memory import InMemoryStorage
from .schemas import (
    AgentConfig,
    AgentHandoffResult,
    Author,
    CompletionRequest,
    CompletionResponse,
    MessageParam,
    RunMetadata,
    ToolCallToolUseBlock,
    ToolResponseWrapper,
)
from .schemas.anthropic import ToolResultContent, ToolResultMessage
from .tools import Tool, ToolManager

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: AgentConfig, agent_manager: "AgentManager"):  # type: ignore # noqa: F821
        self.id = config.id
        self.config = config
        self.tool_manager = ToolManager()
        self.memory = InMemoryStorage()
        self.client: LLMClient = LLMClient(self.config)
        self.metadata: Optional[RunMetadata] = None
        self.agent_manager = agent_manager
        self.description = self._generate_description()
        self.other_agents_info = ""
        self.tool_json = None

    def get_system_message(self) -> MessageParam:
        instruction = f"## IMPORTANT: Your name is {self.config.name} and id is {self.config.id}."
        if self.config.instruction:
            instruction = f"{self.config.instruction} \n\n{instruction}"
        if self.other_agents_info:
            instruction += f"\n\nYou are aware of the following other agents:\n{self.other_agents_info} \n\nYou must use chat_with_agent when you talk to other agents, if you don't use it, the default is to user."
        return MessageParam(role="system", name=self.config.name, content=instruction)

    def get_messages(self) -> List:
        """Retrieve the original list of messages from the Pydantic model."""
        return self.memory.messages

    def get_message_params(self) -> List[Dict]:
        """Retrieve a list of message parameter dictionaries for the completion API call."""
        return self.memory.get_message_params(self.config.model.id)

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
        description += f" Agent {self.config.id} is able to use these tools: {', '.join(tool_names)}"
        return description

    def add_tool_to_agent(self, tool: Union[Callable, Tool]) -> None:
        self.config.tools.append(tool)
        logger.debug(f"Added tool {tool} to agent {self.id}")

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
            self.tool_json = self.tool_manager.get_tool_definitions(self.config.model.id, self.config.tools)
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
        # Add system message if it doesn't exist
        if messages_dict[0]["role"] != "system":
            messages_dict.insert(0, self.get_system_message().model_dump(exclude_none=True))

        completion_request = CompletionRequest(
            author=Author(name=self.config.name, role="assistant") if not author else author,
            model=self.config.model.id,
            messages=messages_dict,
            metadata=metadata,
            tool_json=self.tool_json,
        )
        response = await self.client.send_completion_request(completion_request)
        usage = response.get_usage()
        if usage:
            logger.debug(f"completion response usage: {usage.model_dump(exclude_none=True)}")
        return response

    async def process_tools_with_timeout(
        self,
        tool_calls: List[ToolCallToolUseBlock],
        timeout: int = 30,
        author: Optional[Author] = None,
    ) -> ToolResponseWrapper:
        tool_responses = []
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
                tool_responses.append(self.create_error_response(tool_id, tool_name, error_message))
                continue

            if tool_name == chat_with_agent:
                handoff_result = await self.chat_with_agent(**kwargs)
                return ToolResponseWrapper(agent_handoff_result=handoff_result)
            else:
                tool_func = self.tool_manager.tools[tool_name]
            task = asyncio.create_task(self.run_tool(tool_func, **kwargs))
            tasks.append((task, tool_id, tool_name))

        for task, tool_id, tool_name in tasks:
            try:
                tool_response = await asyncio.wait_for(task, timeout=timeout)
                tool_responses.append(self.create_success_response(tool_id, tool_name, str(tool_response)))
            except asyncio.TimeoutError:
                error_message = f"Timeout while calling tool <{tool_name}> after {timeout}s."
                tool_responses.append(self.create_error_response(tool_id, tool_name, error_message))
            except Exception as e:
                error_message = f"Error while calling tool <{tool_name}>: {e}"
                tool_responses.append(self.create_error_response(tool_id, tool_name, error_message))

        response = None
        if "claude" in self.config.model.id:
            tool_result_message = ToolResultMessage(role="user", content=tool_responses)
            response = ToolResponseWrapper(tool_result_message=tool_result_message, author=author)
        else:
            response = ToolResponseWrapper(tool_messages=tool_responses, author=author)

        return response

    async def run_tool(self, tool_func, **kwargs):
        return await tool_func(**kwargs)

    def create_success_response(self, tool_id: str, tool_name: str, content: str):
        if "claude" in self.config.model.id:
            # return ToolResultBlockParam(tool_use_id=tool_id, content=content, type="tool_result", is_error=False)
            return ToolResultContent(tool_use_id=tool_id, content=content, type="tool_result", is_error=False)
        else:
            return ToolMessageParam(tool_call_id=tool_id, name=tool_name, role="tool", content=content)

    def create_error_response(self, tool_id: str, tool_name: str, error_message: str):
        if "claude" in self.config.model.id:
            result_param = ToolResultContent(
                tool_use_id=tool_id, content=error_message, type="tool_result", is_error=True
            )
            return result_param
        else:
            return ToolMessageParam(tool_call_id=tool_id, name=tool_name, role="tool", content=error_message)

    def build_next_agent_context(self, to_agent_id: str, message: str) -> List[Dict]:
        history = copy.deepcopy(self.get_messages())
        # remove the transfer tool call and append message from calling agent
        # in this way, we keep the conversation cohensive with less noise
        max_messages = 15
        start_idx = max(0, len(history) - (max_messages + 1))  # -11 to account for the -1 later
        messages = history[start_idx:-1]
        messages_content = ",".join([str(msg) for msg in messages])

        messages_content = ",".join([str(msg) for msg in messages])
        history = MessageParam(
            role="assistant",
            content=f"This is some context from conversation between agent {self.id} and other agents: <background>{messages_content}</background> \n\nThe following message is from {self.id} to {to_agent_id}",
        )
        from_agent_message = MessageParam(role="assistant", content=message, name=self.config.name)
        messages.append(from_agent_message)
        messages = [history, from_agent_message]
        return messages
