import asyncio
import json

import httpx
from memory.memory import MemoryInterface
from schemas.anthropic import (
    AnthropicAssistantMessage,
    Message,
    MessageParam,
    ToolResultContent,
    ToolResultMessage,
    ToolUseContent,
)
from schemas.request_metadata import Metadata
from tools.tool_manager import ToolManager
from utils.logs import logger

_tag = "[AnthropicClient]"


class AnthropicClient:
    """
    - https://docs.anthropic.com/en/docs/quickstart
    - https://docs.anthropic.com/en/docs/about-claude/models
    """

    def __init__(
        self,
        api_key,
        model: str = "claude-3-5-sonnet-20240620",
        tool_manager: ToolManager | None = None,
    ):
        self.http_client = httpx.AsyncClient(timeout=60)
        self.chat_completions_url = "https://api.anthropic.com/v1/messages"
        self.api_key = api_key
        self.model = model
        self.tool_manager: ToolManager = tool_manager
        # logger.debug(f"{_tag} model: {model}, self.model: {self.model}")
        if self.tool_manager is not None:
            self.tool_json = self.tool_manager.get_tools_json(model=self.model)
        else:
            self.tool_json = None
        # https://docs.anthropic.com/en/docs/build-with-claude/tool-use
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        logger.debug(f"{_tag} model: {model}")

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
        logger.debug(f"{_tag} send_completion_request model: {self.model}, tools: {self.tool_manager.tools}")
        chat_completion: Message = await self._send_completion_request(messages=messages)
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
        logger.debug(f"{_tag} send_completion_request model: {self.model}, tools: {self.tool_manager.tools}")
        system_messages = [msg for msg in messages if msg.role == "system"]
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag} send_completion_request message ({idx}/{length}): {message.model_dump()}")
        # reference: https://docs.anthropic.com/en/docs/quickstart-guide
        body = {
            "model": self.model,
            "messages": [msg.model_dump(exclude="name") for msg in messages if msg.role != "system"],
            "max_tokens": 4096,
            "temperature": 0.0,
            # "response_format": {"type": "text"},
        }
        if len(system_messages) > 0:
            body["system"] = system_messages[0].content

        if self.tool_json and len(self.tool_json) > 0:
            logger.debug(f"{_tag} send_completion_request response self.tool_json: {len(self.tool_json)}")
            body["tools"] = self.tool_json

        data_json = json.dumps(body)
        response = await self.http_client.post(self.chat_completions_url, headers=self.headers, data=data_json)

        if response.status_code != 200:
            logger.error(f"{_tag} send_completion_request error:\n{response.text}")
            raise Exception(status_code=response.status_code, detail=response.text)

        response_data = response.json()
        logger.debug(f"{_tag} send_completion_request response: {response_data}")

        chat_completion = Message(**response_data)
        logger.info(f"send_completion_request usage: {chat_completion.usage.model_dump()}")
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

    def process_tools(self, tool_use_contents: list[ToolUseContent], tools_dict) -> list[ToolResultContent]:
        tool_result_content_list: list[ToolResultContent] = []
        for tool_use_content in tool_use_contents:
            print(f"Processing tool use: {tool_use_contents}")
            tool_name = tool_use_content.name
            tool_input = tool_use_content.input

            if tool_name in tools_dict:
                tool_function = tools_dict[tool_name]
                tool_response = tool_function(**tool_input)
                tool_result_content = ToolResultContent(
                    type="tool_result",
                    tool_use_id=tool_use_content.id,
                    content=str(tool_response),
                )
            else:
                tool_result_content = ToolResultContent(
                    type="tool_result",
                    tool_use_id=tool_use_content.id,
                    content=f"Error: Tool '{tool_name}' not found",
                )
            print(f"tool_result_content: {tool_result_content}")
            tool_result_content_list.append(tool_result_content)
        return tool_result_content_list

    async def process_tools_with_timeout(self, tool_calls: list[ToolUseContent], timeout=5) -> list[ToolResultContent]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolResultContent] = []

        tasks = []
        for tool in tool_calls:
            tool_func = self.tool_manager.tools[tool.name]
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