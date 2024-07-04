import asyncio
import json

import httpx
from llm_client.llm_model import ChatModel
from llm_client.llm_request import LLMRequest
from memory.memory import MemoryInterface
from schemas.assistant import AssistantMessage, convert_to_assistant_message
from schemas.chat_completion import ChatCompletion
from schemas.error import ErrorResponse
from schemas.message_param import ChatCompletionMessageParam
from schemas.request_metadata import Metadata
from schemas.tool_call import ToolCall
from schemas.tool_message import ToolMessage
from tools.tool_manager import ToolManager
from utils.logs import logger

_tag = "[OpenAIClient]"


class OpenAIClient(LLMRequest):
    def __init__(
        self,
        api_key,
        model: str = ChatModel.GPT_4O.value,
        tool_manager: ToolManager | None = None,
    ):
        self.http_client = httpx.AsyncClient(timeout=60)
        self.chat_completions_url = "https://api.openai.com/v1/chat/completions"
        self.api_key = api_key
        self.model = model
        self.tool_manager = tool_manager
        if self.tool_manager is not None:
            self.tool_json = self.tool_manager.get_tools_json()
        else:
            self.tool_json = None
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        logger.info(f"OpenAIClient initialized with model: {model}, tools: {len(self.tool_json)}")

    async def _send_completion_request(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> ChatCompletion:
        body = {
            "model": self.model,
            "messages": [msg.model_dump() for msg in messages],
            "max_tokens": 2048,
            "temperature": 0.8,
            "response_format": {"type": "text"},
        }

        if self.tool_json and len(self.tool_json) > 0:
            body["tools"] = self.tool_json
            body["tool_choice"] = "auto"

        response = await self.http_client.post(self.chat_completions_url, headers=self.headers, json=body)

        if response.status_code != 200:
            logger.error(f"{_tag} send_completion_request error:\n{response.text}")
            raise Exception(response.text)

        response_data = response.json()
        logger.debug(f"{_tag} send_completion_request response:\n{json.dumps(response_data, indent=2)}")
        chat_completion = ChatCompletion(**response_data)
        logger.info(f"send_completion_request usage: {chat_completion.usage.model_dump()}")
        return chat_completion

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

    def process_tools(self, tool_calls):
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}")
        tool_call_responses: list[str] = []
        for _index, tool_call in enumerate(tool_calls):
            tool_call_id = tool_call.id
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            logger.debug(f"[chat_completion] process tool call <{function_name}>, args: {function_args}")

            function_to_call = self.tool_manager.tools.get(function_name)

            tool_response: str | None = None
            try:
                tool_response = function_to_call(**function_args)
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    role="tool",
                    name=function_name,
                    content=str(tool_response),
                )
                tool_call_responses.append(tool_response_message)
            except Exception as e:
                tool_response = f"Error while calling function <{function_name}>: {e}"

        return tool_call_responses

    async def process_tools_with_timeout(self, tool_calls: list[ToolCall], timeout=5) -> list[ToolMessage]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolMessage] = []

        tasks = []
        for tool_call in tool_calls:
            tool_func = self.tool_manager.tools[tool_call.function.name]
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
