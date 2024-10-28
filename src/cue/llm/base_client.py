import asyncio
import json
import logging

from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam

from ..schemas import AgentConfig, ToolCallToolUseBlock
from ..tools import ToolManager
from .llm_model import ChatModel

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, config: AgentConfig):
        self.model = config.model
        self.tools = config.tools
        self.tool_manager = ToolManager()
        chat_model = ChatModel.from_model_id(config.model)
        if chat_model.tool_use_support and len(self.tools) > 0:
            self.tool_json = self.tool_manager.get_tool_definitions(self.model, self.tools)
        else:
            self.tool_json = None

    async def process_tools_with_timeout(
        self, tool_calls: list[ToolCallToolUseBlock], timeout=5
    ) -> list[ToolMessageParam]:
        logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
        tool_responses: list[ToolMessageParam] = []

        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            if tool_name not in self.tool_manager.tools:
                logger.error(f"Tool '{tool_name}' not found.")
                tool_response_message = ToolMessageParam(
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
                tool_response_message = ToolMessageParam(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=str(tool_response),
                )
                tool_responses.append(tool_response_message)
            except asyncio.TimeoutError:
                logger.error(f"Timeout while calling tool <{function_name}>")
                tool_response = f"Timeout while calling tool <{function_name}> after {timeout}s."
                tool_response_message = ToolMessageParam(
                    tool_call_id=tool_call_id,
                    name=function_name,
                    content=tool_response,
                )
                tool_responses.append(tool_response_message)
            except Exception as e:
                logger.error(f"Error while calling tool <{function_name}>: {e}")
                tool_response = f"Error while calling tool <{function_name}>: {e}"
                tool_response_message = ToolMessageParam(
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
