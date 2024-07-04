import asyncio
import json

from core.chat_base import ChatBase
from memory.memory import MemoryInterface
from schemas.error import ErrorResponse
from schemas.request_metadata import Metadata
from schemas.tool_call import AssistantMessage, ToolMessage, convert_to_assistant_message
from tools.tool_manager import ToolManager
from utils.logs import logger

tools_manager = ToolManager()
chat_base = ChatBase(tools=tools_manager.get_tools_json())


async def send_completion_request(memory: MemoryInterface | None = None, metadata: Metadata = None) -> dict:
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
    response = await chat_base.send_request(schema_messages, use_tools=True)
    if isinstance(response, ErrorResponse):
        return response

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls is None:
        message = AssistantMessage(**response.choices[0].message.model_dump())
        await memory.save(message)
        return response  # return original response
    tool_call_message = convert_to_assistant_message(response.choices[0].message)
    await memory.save(tool_call_message)
    tool_responses = await process_tool_calls(tool_calls)
    await memory.saveList(tool_responses)

    metadata = Metadata(
        last_user_message=metadata.last_user_message,
        current_depth=metadata.current_depth + 1,
        total_depth=metadata.total_depth + 1,
    )

    return await send_completion_request(memory=memory, metadata=metadata)


async def run_tool(tool_func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, tool_func, *args)


async def process_tool_calls(tool_calls, timeout=5) -> list[ToolMessage]:
    logger.debug(f"[chat_completion] process tool calls count: {len(tool_calls)}, timeout: {timeout}")
    tool_call_responses: list[ToolMessage] = []

    tasks = []
    for tool_call in tool_calls:
        tool_func = tools_manager.tools[tool_call.function.name]
        args = tuple(json.loads(tool_call.function.arguments).values())
        task = asyncio.create_task(run_tool(tool_func, *args))
        tasks.append((task, tool_call))

    for task, tool_call in tasks:
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        try:
            function_response = await asyncio.wait_for(task, timeout=timeout)
            tool_response_message = ToolMessage(
                tool_call_id=tool_call_id,
                role="tool",
                name=function_name,
                content=str(function_response),
            )
            tool_call_responses.append(tool_response_message)
        except asyncio.TimeoutError:
            logger.error(f"Timeout while calling function <{function_name}>")
            function_response = f"Timeout while calling function <{function_name}> after {timeout}s."
            tool_response_message = ToolMessage(
                tool_call_id=tool_call_id,
                role="tool",
                name=function_name,
                content=function_response,
            )
            tool_call_responses.append(tool_response_message)
        except Exception as e:
            logger.error(f"Error while calling function <{function_name}>: {e}")
            function_response = f"Error while calling function <{function_name}>: {e}"
            tool_response_message = ToolMessage(
                tool_call_id=tool_call_id,
                role="tool",
                name=function_name,
                content=function_response,
            )
            tool_call_responses.append(tool_response_message)

    return tool_call_responses
