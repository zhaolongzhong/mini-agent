import logging
from typing import Optional

from pydantic import BaseModel

from .string_utils import truncate_safely

logger = logging.getLogger(__name__)


def has_tool_calls(msg: dict) -> bool:
    """Check if a message contains tool calls."""

    def get_role(msg) -> str:
        if isinstance(msg, BaseModel):
            return msg.role if hasattr(msg, "role") else None
        return msg.get("role")

    role = get_role(msg)
    if role != "assistant":
        return False

    if msg.get("tool_calls", []):
        return True

    if isinstance(msg.get("content", []), list):
        for item in msg.get("content", []):
            if isinstance(item, dict) and item.get("type") == "tool_use":
                return True

    return msg.get("type", "") == "tool_use"


def is_tool_result(msg: dict) -> bool:
    """Check if a message is a tool result."""

    def get_role(msg) -> str:
        if isinstance(msg, BaseModel):
            return msg.role if hasattr(msg, "role") else None
        return msg.get("role")

    role = get_role(msg)
    if role == "tool":
        return True
    if role != "user":
        return False
    if isinstance(msg.get("content", []), list):
        for item in msg.get("content", []):
            if isinstance(item, dict) and item.get("type") == "tool_result":
                return True
    return msg.get("type", "") == "tool_result"


def get_text_from_message_params(
    model: str,
    messages: list[dict],
    content_max_length: Optional[int] = 100,
) -> str:
    if "claude" in model:
        return get_text_from_message_params_claude(
            messages=messages,
            content_max_length=content_max_length,
        )
    return get_text_from_message_params_openai(
        messages=messages,
        content_max_length=content_max_length,
    )


def get_text_from_message_params_claude(
    messages: list[dict],
    content_max_length: Optional[int] = 100,
) -> str:
    message_content = ""

    for _idx, msg in enumerate(messages):
        role = msg.get("role", None)

        if role == "user":
            text = ""
            if is_tool_result(msg):
                results = msg.get("content", [])
                for result in results:
                    text += f"type: tool_result, tool_use_id: {result['tool_use_id']}"
                    for content in result.get("content", []):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        elif content.get("type", None) == "image":
                            text += "skip image content"
                        else:
                            logger.error(f"Unhandled type: {msg}")
            else:
                if isinstance(msg.get("content"), str):
                    text += truncate_safely(msg.get("content"), content_max_length)
                elif isinstance(msg.get("content"), list):
                    for content in msg.get("content"):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        elif content.get("type", None) == "image":
                            text += "skip image content"
                        else:
                            logger.error(f"Unexpected content: {msg}")
            if text:
                message_content += text + "\n"
        elif role == "assistant":
            text = ""
            if has_tool_calls(msg):
                for content in msg.get("content", []):
                    if content.get("type", None) == "text":
                        text += truncate_safely(content.get("text"), content_max_length)
                    elif content.get("type", None) == "tool_use":
                        text += f"type: tool_use, id: {content.get('id', '')}, name: {content.get('name', '')}"
                        text += truncate_safely(str(content.get("input")), content_max_length)
                    else:
                        logger.error(f"Unhandled type: {msg}")
            else:
                if isinstance(msg.get("content"), str):
                    text += truncate_safely(msg.get("content"), content_max_length)
                elif isinstance(msg.get("content"), list):
                    for content in msg.get("content"):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        elif content.get("type", None) == "image":
                            text += "skip image content"
                        else:
                            logger.error(f"Unexpected content: {msg}")
            if text:
                message_content += text + "\n"
        else:
            logger.error(f"Unexpected role: {role}")
    return message_content


def get_text_from_message_params_openai(
    messages: list[dict],
    content_max_length: Optional[int] = 100,
) -> str:
    message_content = ""

    for _idx, msg in enumerate(messages):
        role = msg.get("role", None)

        if role == "user":
            text = ""
            if is_tool_result(msg):
                text += f"name: {msg.get('name','')}, role: tool, tool_call_id: {msg.get('tool_call_id')}"
                text += truncate_safely(msg.get("content"), content_max_length)
            else:
                if isinstance(msg.get("content"), str):
                    text += truncate_safely(msg.get("content"), content_max_length)
                elif isinstance(msg.get("content"), list):
                    for content in msg.get("content"):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        elif content.get("type", None) == "image_url":
                            text += "skip image content"
                        else:
                            logger.error(f"Unexpected content: {msg}")
            if text:
                message_content += text + "\n"
        elif role == "assistant":
            text = ""
            if has_tool_calls(msg):
                # handle content first if there is any
                if isinstance(msg.get("content"), str):
                    text += truncate_safely(msg.get("content"), content_max_length)
                elif isinstance(msg.get("content"), list):
                    for content in msg.get("content"):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        elif content.get("type", None) == "image_url":
                            text += "skip image content"
                        else:
                            logger.error(f"Unexpected content: {msg}")

                # handle tool call
                for tool_call in msg.get("tool_calls", []):
                    if tool_call.get("type", None) == "function":
                        text += f"type: function, id: {tool_call.get('id', '')}, name: {tool_call['function']['name']}"
                        text += truncate_safely(str(tool_call.get("function")), content_max_length)
                    else:
                        logger.error(f"Unhandled type: {msg}")
            else:
                if isinstance(msg.get("content"), str):
                    text += truncate_safely(msg.get("content"), content_max_length)
                elif isinstance(msg.get("content"), list):
                    for content in msg.get("content"):
                        if content.get("type", None) == "text":
                            text += truncate_safely(content.get("text"), content_max_length)
                        else:
                            logger.error(f"Unexpected content: {msg}")
            if text:
                message_content += text
        elif role == "tool":
            text = f"role: tool, tool_call_id: {msg.get('tool_call_id', '')}, name: {msg.get('name', '')}, "
            text += f"content: {truncate_safely(msg.get('content'), content_max_length)}"
            message_content += text + "\n"

        else:
            logger.error(f"Unexpected role: {role}")
    return message_content
