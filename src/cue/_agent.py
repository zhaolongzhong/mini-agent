import asyncio
import json
import logging
from typing import Dict, List, Optional, Union

from anthropic.types import ToolUseBlock
from openai.types.chat import ChatCompletionMessageToolCall as ToolCall
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from .llm.llm_client import LLMClient
from .memory.memory import InMemoryStorage
from .schemas import (
    AgentConfig,
    Author,
    CompletionRequest,
    CompletionResponse,
    MessageParam,
    RunMetadata,
    ToolCallToolUseBlock,
    ToolResponseWrapper,
)
from .schemas.anthropic import ToolResultContent, ToolResultMessage
from .tools import ToolManager

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

    def get_system_message(self) -> MessageParam:
        instruction = (
            f"{self.config.instruction} \n\n### IMPORTANT: Your name is {self.config.name} and id is {self.config.id}."
        )
        if self.other_agents_info:
            instruction += f"\n\nYou are aware of the following other agents:\n{self.other_agents_info} \n\nYou must use chat_with_agent when you talk to other agents, if you don't use it, the default is to user."
        return MessageParam(role="system", name=self.config.name, content=instruction)

    def get_messages(self) -> List:
        """
        Retrieve the original list of messages from the Pydantic model.

        Returns:
            List: A list of message objects stored in the memory.
        """
        return self.memory.messages

    def get_message_params(self) -> List[Dict]:
        """
        Retrieve a list of message parameter dictionaries for the completion API call.

        Returns:
            List[Dict]: A list of dictionaries containing message parameters
                        required for the completion API call, based on the model ID
                        from the current configuration.
        """
        return self.memory.get_message_params(self.config.model.id)

    def _generate_description(self) -> str:
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

    def _get_tool_json(self) -> Optional[List[Dict]]:
        if self.config.tools:
            res = self.tool_manager.get_tool_definitions(self.config.model.id, self.config.tools)
            return res
        else:
            return None

    async def run(self, author: Optional[Author] = None):
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
            tool_json=self._get_tool_json(),
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
            if tool_name not in self.tool_manager.tools and tool_name not in ["call_agent", chat_with_agent]:
                error_message = f"Tool '{tool_name}' not found. {self.tool_manager.tools.keys()}"
                logger.error(f"{error_message}, tool_call: {tool_call}")
                tool_responses.append(self.create_error_response(tool_id, tool_name, error_message))
                continue

            if tool_name == chat_with_agent:
                tool_func = self.agent_manager.chat_with_agent
                if "from_agent_id" in kwargs:
                    kwargs["from_agent_id"] = self.id
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
