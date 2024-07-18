import asyncio
import json

import httpx
import openai
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


class OpenAIClient(LLMRequest):
    def __init__(
        self,
        api_key,
        config: AgentConfig,
    ):
        self.http_client = httpx.AsyncClient(timeout=60)
        self.chat_completions_url = "https://api.openai.com/v1/chat/completions"
        self.api_key = api_key
        self.model = config.model
        self.tools = config.tools
        self.tool_manager = ToolManager()
        if len(self.tools) > 0:
            self.tool_json = self.tool_manager.get_tool_definitions(self.model, self.tools)
        else:
            self.tool_json = None
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        logger.info(f"[OpenAIClient] initialized with model: {self.model}, tools: {[tool.name for tool in self.tools]}")

    async def _send_completion_request(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> ChatCompletion:
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag}send_completion_request message ({idx + 1}/{length}): {message.model_dump()}")

        body = {
            "model": self.model.model_id,
            "messages": [
                msg.model_dump(exclude={"tool_calls"})
                if hasattr(msg, "tool_calls") and not msg.tool_calls
                else msg.model_dump()
                for msg in messages
            ],
            "max_tokens": 2048,
            "temperature": 0.8,
            "response_format": {"type": "text"},
        }

        if self.tool_json and len(self.tool_json) > 0:
            body["tools"] = self.tool_json
            body["tool_choice"] = "auto"

        try:
            response = await self.http_client.post(self.chat_completions_url, headers=self.headers, json=body)

            if response.status_code != 200:
                logger.error(f"{_tag}send_completion_request error:\n{response.text}")
                raise Exception(response.text)

            response_data = response.json()
            logger.debug(f"{_tag}send_completion_request response:\n{json.dumps(response_data, indent=2)}")
            chat_completion = ChatCompletion(**response_data)
            logger.info(f"send_completion_request usage: {chat_completion.usage.model_dump()}")
            return chat_completion
        except openai.APIConnectionError as e:
            return ErrorResponse(message=f"The server could not be reached. {e.__cause__}")
        except openai.RateLimitError as e:
            return ErrorResponse(
                message=f"A 429 status code was received; we should back off a bit. {e.response}",
                code=str(e.status_code),
            )
        except openai.APIStatusError as e:
            message = f"Another non-200-range status code was received. {e.response}, {e.response.text}"
            logger.error(f"{message}")
            return ErrorResponse(
                message=message,
                code=str(e.status_code),
            )
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
        metadata.current_depth += 1
        metadata.total_depth += 1
        metadata.request_count += 1

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            message = AssistantMessage(**response.choices[0].message.model_dump())
            await memory.save(message)
            return response  # return original response
        tool_call_message = convert_to_assistant_message(response.choices[0].message)
        await memory.save(tool_call_message)
        tool_responses = await self.process_tools_with_timeout(tool_calls, timeout=5)
        await memory.saveList(tool_responses)

        return await self.send_completion_request(memory=memory, metadata=metadata)

    async def process_tools_with_timeout(self, tool_calls: list[ToolCall], timeout=5) -> list[ToolMessage]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolMessage] = []

        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            # if use generic command approach for tool, sometimes tool name is in the format of <manage_drive.get_by_folder_id>
            tool_name = tool_name if "." not in tool_name else tool_name.split(".")[0]
            if tool_name not in self.tool_manager.tools:
                logger.error(f"Tool '{tool_name}' not found.")
                tool_response_message = ToolMessage(
                    tool_call_id=tool_call.id,
                    name=tool_name if "." not in tool_name else None,
                    content=f"Tool<{tool_name}> not found, available tools: "
                    + ", ".join(self.tool_manager.tools.keys()),
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
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(*args)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, tool_func, *args)
