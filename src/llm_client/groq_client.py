import asyncio
import json

from groq import AsyncGroq
from llm_client.llm_request import LLMRequest
from memory.memory import MemoryInterface
from schemas.agent import AgentConfig
from schemas.assistant import AssistantMessage, convert_to_assistant_message
from schemas.chat_completion import ChatCompletion
from schemas.error import ErrorResponse
from schemas.message_param import ChatCompletionMessageParam
from schemas.request_metadata import Metadata
from schemas.tool_call import ToolCall
from schemas.tool_message import ToolMessage
from tools.tool_manager import ToolManager
from utils.logs import logger

_tag = ""


class GroqClient(LLMRequest):
    """https://console.groq.com/docs/quickstart"""

    def __init__(
        self,
        api_key,
        config: AgentConfig,
    ):
        self.client = AsyncGroq(
            api_key=api_key,
        )
        self.api_key = api_key
        self.model = config.model
        self.tools = config.tools
        self.tool_manager = ToolManager()
        if len(self.tools) > 0:
            self.tool_json = self.tool_manager.get_tools_json(self.model, self.tools)
        else:
            self.tool_json = None

        logger.info(f"[GroqClient] initialized with model: {self.model}, tools: {[tool.name for tool in self.tools]}")

    async def _send_completion_request(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> ChatCompletion:
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag}send_completion_request message ({idx + 1}/{length}): {message.model_dump()}")

        try:
            if self.tool_json and len(self.tool_json) > 0:
                chat_completion = await self.client.chat.completions.create(
                    messages=[msg.model_dump(exclude="name") for msg in messages],
                    model=self.model,
                    tools=self.tool_json,
                    tool_choice="auto",
                    max_tokens=2048,
                    temperature=0.8,
                )
            else:
                chat_completion = await self.client.chat.completions.create(
                    messages=[msg.model_dump() for msg in messages],
                    model=self.model,
                )

            chat_completion = ChatCompletion(**chat_completion.model_dump())
            logger.info(f"send_completion_request usage: {chat_completion.usage.model_dump()}")
            return chat_completion
        except Exception as e:
            return ErrorResponse(
                message=f"Exception: {e}",
            )

    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ) -> dict | None:
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

        schema_messages = memory.get_message_params()
        response = await self._send_completion_request(schema_messages)
        if isinstance(response, ErrorResponse):
            return response

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            logger.debug(f"[chat_completion] no tool calls found in response. response: {response.choices[0].message}")
            message = AssistantMessage(**response.choices[0].message.model_dump())
            await memory.save(message)
            return response  # return original response
        tool_call_message = convert_to_assistant_message(response.choices[0].message)
        await memory.save(tool_call_message)
        tool_responses = await self.process_tools_with_timeout(tool_calls, timeout=5)
        await memory.saveList(tool_responses)

        metadata = Metadata(
            last_user_message=metadata.last_user_message,
            current_depth=metadata.current_depth + 1,
            total_depth=metadata.total_depth + 1,
        )

        return await self.send_completion_request(memory=memory, metadata=metadata)

    async def process_tools_with_timeout(self, tool_calls: list[ToolCall], timeout=5) -> list[ToolMessage]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolMessage] = []

        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in self.tool_manager.tools:
                logger.error(f"Tool '{tool_name}' not found.")
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call.id,
                    name=tool_name,
                    content="Tool not found",
                )
                tool_responses.append(tool_response_message)
                continue

            tool_func = self.tool_manager.tools[tool_name]
            args = tuple(json.loads(tool_call.function.arguments).values())
            task = asyncio.create_task(self.run_tool(tool_func, *args))
            tasks.append((task, tool_call))

        for task, tool_call in tasks:
            tool_call_id = tool_call.id
            function_name = tool_call.function.name
            try:
                tool_response = await asyncio.wait_for(task, timeout=timeout)
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=str(tool_response),
                )
                tool_responses.append(tool_response_message)
            except asyncio.TimeoutError:
                logger.error(f"Timeout while calling tool <{function_name}>")
                tool_response = f"Timeout while calling tool <{function_name}> after {timeout}s."
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=tool_response,
                )
                tool_responses.append(tool_response_message)
            except Exception as e:
                logger.error(f"Error while calling tool <{function_name}>: {e}")
                tool_response = f"Error while calling tool <{function_name}>: {e}"
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=tool_response,
                )
                tool_responses.append(tool_response_message)

        return tool_responses

    async def run_tool(self, tool_func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, tool_func, *args)
