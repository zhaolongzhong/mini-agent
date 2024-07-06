import os

from llm_client.llm_model import ChatModel
from schemas.anthropic import AnthropicAssistantMessage, ToolResultMessage
from schemas.message import Message
from schemas.message_param import MessageLike
from schemas.tool_call import AssistantMessage, ToolMessage
from utils.json_utils import append_jsonl, get_jsonl
from utils.logs import logger

_tag = "[MemoryUtils]"


def load_from_memory(full_path: str, model: ChatModel = None):
    logger.debug(f"{_tag} load_from_memory: {full_path}")
    system_message = Message(role="system", content="You're a helpful assistant!")
    directory = os.path.dirname(full_path)
    # Read file from memory.jsonl, use this file to store json lines as memory
    if directory and not os.path.exists(directory):
        logger.debug(f"Creating directory {directory}")
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(full_path):
        # If the file does not exist, create an empty file
        try:
            with open(full_path, "a", encoding="utf-8") as f:
                f.close()
                logger.info(f"Created new file at: {full_path}")
                save_to_memory(full_path, system_message)
                return [system_message]
        except Exception as error:
            return f"Error: {error}"

    try:
        messages = get_jsonl(full_path)
        if len(messages) == 0:
            save_to_memory(full_path, system_message)
            return [system_message]
        validated_messages = []
        if model and "claude" in model.name.lower():
            for message in messages:
                if "role" in message and message.get("role") == "system":
                    validated_messages.append(Message(**message))
                elif "role" in message and message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, list):
                        if any("tool_result" in item.get("type", "") for item in content):
                            validated_messages.append(ToolResultMessage(**message))
                        else:
                            validated_messages.append(Message(**message))
                    else:
                        validated_messages.append(Message(**message))
                elif "role" in message and message.get("role") == "assistant":
                    validated_messages.append(AnthropicAssistantMessage(**message))
                else:
                    raise ValueError(f"Invalid message: {message}")
            return validated_messages
        else:
            for message in messages:
                if "tool_calls" in message and isinstance(message.get("tool_calls"), list):
                    validated_messages.append(AssistantMessage(**message))
                elif "tool_call_id" in message and isinstance(message.get("tool_call_id"), str):
                    # Use ToolCallMessage for messages where 'tool_calls' is a top-level key
                    validated_messages.append(ToolMessage(**message))
                elif "role" in message and message.get("role") == "system":
                    validated_messages.append(Message(**message))
                elif "role" in message and message.get("role") == "user":
                    validated_messages.append(Message(**message))
                elif "role" in message and message.get("role") == "assistant":
                    validated_messages.append(AssistantMessage(**message))
                elif "role" in message and message.get("role") == "tool":
                    validated_messages.append(ToolMessage(**message))
                else:
                    raise ValueError(f"Invalid message: {message}")
            return validated_messages
    except Exception as e:
        logger.error(f"Error in load_from_memory: {e}, path: {full_path}")
        return []


def save_to_memory(path, data: MessageLike):
    try:
        data_dict = data.model_dump()
        append_jsonl(data_dict, path)
    except Exception as e:
        logger.error(f"Error in save_to_memory: {e}, path: {path}, data: {data}")
