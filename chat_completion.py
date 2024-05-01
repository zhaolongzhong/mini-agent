import json

from core.chat_base import ChatBase
from models.error import ErrorResponse
from models.message import Message
from models.tool_call import ToolResponseMessage, convert_to_tool_call_message
from tools.available_tools import available_tools, tools_list
from utils.logs import log

chat_base = ChatBase(tools=tools_list)


async def send_completion_request(messages: list = None) -> dict:
    if messages is None:
        messages = [Message(role="system", content="You are a helpful assistant.")]

    response = await chat_base.send_request(messages, use_tools=True)
    if isinstance(response, ErrorResponse):
        return response

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls is None:
        return response

    tool_call_message = convert_to_tool_call_message(response.choices[0].message)
    messages.append(tool_call_message)
    tool_responses = process_tool_calls(tool_calls)
    messages.extend(tool_responses)
    return await chat_base.send_request(messages, use_tools=True)


def process_tool_calls(tool_calls):
    log.debug("[chat_completion] process tool calls")
    tool_call_responses: list[str] = []
    for _index, tool_call in enumerate(tool_calls):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        function_to_call = available_tools.get(function_name)

        function_response: str | None = None
        try:
            function_response = function_to_call(**function_args)
            tool_response_message = ToolResponseMessage(
                tool_call_id=tool_call_id,
                role="tool",
                name=function_name,
                content=str(function_response),
            )
            tool_call_responses.append(tool_response_message)
        except Exception as e:
            function_response = f"Error while calling function <{function_name}>: {e}"

    return tool_call_responses
