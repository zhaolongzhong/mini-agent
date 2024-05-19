import json

from core.chat_base import ChatBase
from memory.memory import MemoryInterface
from models.error import ErrorResponse
from models.request_metadata import Metadata
from models.tool_call import ToolMessage, convert_to_assistant_message
from tools.tool_manager import ToolManager
from utils.logs import log

tools_mananger = ToolManager()
chat_base = ChatBase(tools=tools_mananger.get_tools_json())


async def send_completion_request_simple(
    messages: list = None, metadata: Metadata = None
) -> dict:
    if metadata is None:
        metadata = Metadata()

    if metadata.current_depth >= metadata.max_depth:
        response = input(
            f"Maximum depth of {metadata.max_depth} reached. Continue?" " (y/n): "
        )
        if response.lower() in ["y", "yes"]:
            metadata.current_depth = 0
        else:
            return None

    response = await chat_base.send_request(messages, use_tools=True)
    if isinstance(response, ErrorResponse):
        return response

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls is None:
        return response

    tool_call_message = convert_to_assistant_message(response.choices[0].message)
    messages.append(tool_call_message)
    tool_responses = process_tool_calls(tool_calls)
    messages.extend(tool_responses)

    metadata = Metadata(
        last_user_message=metadata.last_user_message,
        current_depth=metadata.current_depth + 1,
        total_depth=metadata.total_depth + 1,
    )

    return await send_completion_request_simple(messages=messages, metadata=metadata)


async def send_completion_request(
    memory: MemoryInterface = None, metadata: Metadata = None
) -> dict:
    if metadata is None:
        metadata = Metadata()

    if metadata.current_depth >= metadata.max_depth:
        response = input(
            f"Maximum depth of {metadata.max_depth} reached. Continue?" " (y/n): "
        )
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
        return response
    tool_call_message = convert_to_assistant_message(response.choices[0].message)
    await memory.save(tool_call_message)
    tool_responses = process_tool_calls(tool_calls)
    await memory.saveList(tool_responses)

    metadata = Metadata(
        last_user_message=metadata.last_user_message,
        current_depth=metadata.current_depth + 1,
        total_depth=metadata.total_depth + 1,
    )

    return await send_completion_request(memory=memory, metadata=metadata)


def process_tool_calls(tool_calls):
    log.debug("[chat_completion] process tool calls")
    tool_call_responses: list[str] = []
    for _index, tool_call in enumerate(tool_calls):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        log.debug(f"[chat_completion] process tool call <{function_name}>")

        function_to_call = tools_mananger.tools.get(function_name)

        function_response: str | None = None
        try:
            function_response = function_to_call(**function_args)
            tool_response_message = ToolMessage(
                tool_call_id=tool_call_id,
                role="tool",
                name=function_name,
                content=str(function_response),
            )
            tool_call_responses.append(tool_response_message)
        except Exception as e:
            function_response = f"Error while calling function <{function_name}>: {e}"

    return tool_call_responses
