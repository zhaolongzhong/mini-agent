import asyncio
import json
import logging

import httpx

from ..config import get_settings
from ..memory.memory import MemoryInterface
from ..schemas import AgentConfig
from ..schemas.anthropic import (
    AnthropicAssistantMessage,
    Message,
    ToolResultContent,
    ToolResultMessage,
    ToolUseContent,
)
from ..schemas.anthropic import (
    AnthropicMessageParam as MessageParam,
)
from ..schemas.request_metadata import Metadata
from ..tool_manager import ToolManager

logger = logging.getLogger(__name__)

_tag = ""


class AnthropicClient:
    """
    - https://docs.anthropic.com/en/docs/quickstart
    - https://docs.anthropic.com/en/docs/about-claude/models
    - https://docs.anthropic.com/en/docs/build-with-claude/tool-use
    """

    def __init__(
        self,
        config: AgentConfig,
    ):
        settings = get_settings()
        api_key = config.api_key or settings.ANTRHOPIC_API_KEY
        if not api_key:
            raise ValueError("API key is missing in both config and settings.")

        self.http_client = httpx.AsyncClient(timeout=60)
        self.chat_completions_url = "https://api.anthropic.com/v1/messages"
        self.api_key = api_key
        self.model = config.model
        self.tools = config.tools
        self.tool_manager: ToolManager = ToolManager()
        if len(self.tools) > 0:
            self.tool_json = self.tool_manager.get_tool_definitions(self.model, self.tools)
        else:
            self.tool_json = None
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        logger.info(
            f"[AnthropicClient] initialized with model: {self.model}, tools: {[tool.name for tool in self.tools]}"
        )

    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ):
        if metadata is None:
            metadata = Metadata()
        else:
            logger.debug(f"Metadata: {metadata.model_dump_json()}")

        if metadata.current_depth >= metadata.max_depth:
            response = input(f"Maximum depth of {metadata.max_depth} reached. Continue?" " (y/n): ")
            if response.lower() in ["y", "yes"]:
                metadata.current_depth = 0
            else:
                return None
        messages = memory.get_message_params()
        chat_completion: Message = await self._send_completion_request(messages=messages)
        metadata.current_depth += 1
        metadata.total_depth += 1
        metadata.request_count += 1
        assistant_message = AnthropicAssistantMessage(**chat_completion.model_dump())
        await memory.save(assistant_message)

        tool_responses = await self.check_and_process_tool_use(chat_completion)
        if len(tool_responses) == 0:
            return chat_completion
        tool_responses_message = ToolResultMessage(role="user", content=tool_responses)

        await memory.save(tool_responses_message)
        return await self.send_completion_request(
            memory=memory,
            metadata=metadata,
        )

    async def _send_completion_request(
        self,
        messages: list[MessageParam],
    ) -> Message:
        logger.debug(f"{_tag}send_completion_request model: {self.model}, tools: {self.tools}")
        # The Messages API accepts a top-level `system` parameter, not \"system\" as an input message role.
        system_messages = [msg for msg in messages if msg.role == "system"]
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag}message ({idx + 1}/{length}): {message.model_dump()}")
        # reference: https://docs.anthropic.com/en/docs/quickstart-guide
        body = {
            "model": self.model.model_id,
            "messages": [msg.model_dump(exclude="name") for msg in messages if msg.role != "system"],
            "max_tokens": 4096,
            "temperature": 0.0,
            # "response_format": {"type": "text"},
        }
        if len(system_messages) > 0:
            logger.debug(f"system_message: {system_messages[0].model_dump()}")
            body["system"] = system_messages[0].content

        if self.tool_json and len(self.tool_json) > 0:
            logger.debug(f"{_tag}send_completion_request response self.tool_json: {len(self.tool_json)}")
            body["tools"] = self.tool_json

        data_json = json.dumps(body)
        response = await self.http_client.post(self.chat_completions_url, headers=self.headers, data=data_json)

        if response.status_code != 200:
            logger.error(f"{_tag}send_completion_request error:\n{response.text}")
            raise Exception(status_code=response.status_code, detail=response.text)

        response_data = response.json()
        chat_completion = Message(**response_data)
        logger.debug(f"usage: {chat_completion.usage.model_dump()}")
        return chat_completion

    async def check_and_process_tool_use(self, message: Message) -> list[ToolResultContent]:
        """Check if the message contains tool use content and process the tools."""
        tool_use_contents = [
            content_item for content_item in message.content if isinstance(content_item, ToolUseContent)
        ]
        if len(tool_use_contents) > 0:
            return await self.process_tools_with_timeout(tool_use_contents, timeout=5)
        else:
            return []

    async def process_tools_with_timeout(self, tool_calls: list[ToolUseContent], timeout=5) -> list[ToolResultContent]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolResultContent] = []

        tasks = []
        for tool in tool_calls:
            tool_name = tool.name
            tool_func = self.tool_manager.tools[tool.name]
            if tool_name not in self.tool_manager.tools:
                logger.error(f"Tool '{tool_name}' not found.")
                tool_response_message = ToolResultContent(
                    tool_call_id=tool.id,
                    name=tool_name,
                    content="Tool not found",
                )
                tool_responses.append(tool_response_message)
                continue
            args = tuple(tool.input.values())
            task = asyncio.create_task(self.run_tool(tool_func, *args))
            tasks.append((task, tool))

        for task, tool in tasks:
            tool_id = tool.id
            tool_name = tool.name
            try:
                tool_response = await asyncio.wait_for(task, timeout=timeout)
                tool_response_message = ToolResultContent(
                    tool_use_id=tool_id,
                    content=str(tool_response),
                )
                tool_responses.append(tool_response_message)
            except asyncio.TimeoutError:
                logger.error(f"Timeout while calling tool <{tool_name}>")
                tool_response = f"Timeout while calling tool <{tool_name}> after {timeout}s."
                tool_response_message = ToolResultContent(
                    tool_use_id=tool_id,
                    content=tool_response,
                )
                tool_responses.append(tool_response_message)
            except Exception as e:
                logger.error(f"Error while calling tool <{tool_name}>: {e}")
                tool_response = f"Error while calling tool <{tool_name}>: {e}"
                tool_response_message = ToolResultContent(
                    tool_use_id=tool_id,
                    content=tool_response,
                )
                tool_responses.append(tool_response_message)

        return tool_responses

    async def run_tool(self, tool_func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, tool_func, *args)
