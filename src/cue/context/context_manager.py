import json
import logging
from typing import Any, Dict, List, Union

from pydantic.main import BaseModel

from ..schemas import MessageParam, CompletionResponse, ToolResponseWrapper
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class DynamicContextManager:
    def __init__(self, max_tokens: int = 4096):
        """
        Initialize the DynamicContextManager with a maximum token limit.

        Args:
            max_tokens (int): Maximum number of tokens to maintain in context
        """
        self.max_tokens = max_tokens
        self.messages: List[Dict] = []
        self.token_counter = TokenCounter()

    def _get_total_tokens(self) -> int:
        """Get the total token count for all messages in the current window."""
        return self.token_counter.count_messages_tokens(self.messages)

    def _count_dict_tokens(self, data: Union[dict, Any]) -> int:
        """Count tokens in a TypedDict or dictionary structure."""
        return self.token_counter.count_dict_tokens(data)

    def _get_total_tokens(self) -> int:
        """Get the rough total token count for all messages in the current window."""
        total_tokens = 0
        for msg in self.messages:
            if isinstance(msg, BaseModel):
                tokens = self._count_tokens(msg.model_dump_json())
                total_tokens += tokens
            elif isinstance(msg, dict):
                tokens = self._count_dict_tokens(msg)
                total_tokens += tokens
            else:
                logger.error(f"Unexpected type in _get_total_tokens: {type(msg)}")

        return total_tokens

    def add_message(
        self, message: Union[CompletionResponse, ToolResponseWrapper, MessageParam, Dict[str, Any], BaseModel]
    ) -> None:
        """Add a new message to the context window and manage token limits."""
        original_size = len(self.messages)

        if isinstance(message, CompletionResponse):
            self.messages.append(message.to_params())
        elif isinstance(message, ToolResponseWrapper):
            if message.tool_messages:
                self.messages.extend(message.tool_messages)
            elif message.tool_result_message:
                self.messages.append(message.tool_result_message)
            else:
                raise Exception(
                    f"Only params or tool result allowed to add message list, receive type: {type(message)}"
                )
        elif isinstance(message, (MessageParam, dict, BaseModel)):
            message_dict = message.model_dump() if isinstance(message, BaseModel) else message
            self.messages.append(message_dict)
        else:
            raise Exception(
                f"Only params, tool result, dict or BaseModel allowed to add message list, receive type: {type(message)}"
            )

        total_tokens = self._get_total_tokens()

        while total_tokens > self.max_tokens and len(self.messages) > 1:

            def get_role(msg) -> str:
                if isinstance(msg, BaseModel):
                    return msg.role if hasattr(msg, "role") else None
                return msg.get("role")

            def has_tool_calls(msg) -> bool:
                """
                Check if a message contains tool calls.
                Handles both BaseModel tool_calls and content list tool use blocks.
                """
                role = get_role(msg)
                if role != "assistant":
                    return False

                # Case 1: Dictionary with tool_calls attribute
                if msg.get("tool_calls", []):
                    return True

                # Case 2: Dictionary with content list containing tool use blocks
                """
                 Example tool use block:
                {
                    'id': 'toolu_xxx',
                    'type': 'tool_use',
                    'name': 'tool_name',
                    'input': {...}
                }
                """
                if isinstance(msg.get("content", []), list):
                    for item in msg.get("content", []):
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            return True

                return msg.get("type", "") == "tool_use"

            def is_tool_result(msg) -> bool:
                role = get_role(msg)
                # Case 1: Dictionary with tool role
                """
                tool_message_param = {
                    "tool_use_id": "tool_id",
                    "name": tool_name,
                    "role": "tool",
                    "content": tool_result_content,
                }
                """
                if role == "tool":
                    return True
                # Case 2: Dictionary with user role
                """
                tool_result_block_param = {
                    "tool_use_id": tool_id,
                    "content": tool_result_content,
                    "type": "tool_result",
                    "is_error": is_error,
                }
                """
                if role != "user":
                    return False
                if isinstance(msg.get("content", []), list):
                    for item in msg.get("content", []):
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            return True
                return msg.get("type", "") == "tool_result"

            # Check if the oldest message is part of a tool call sequence
            if len(self.messages) >= 2 and has_tool_calls(self.messages[0]):
                # Remove both the tool response and the message with tool_calls
                logger.info(f"Tokens {total_tokens}/{self.max_tokens}, pruning tool call & response")
                self.messages.pop(0)  # Remove tool call
                # Keep removing tool result messages until we find a non-tool result
                while len(self.messages) > 0 and is_tool_result(self.messages[0]):
                    removed_message = self.messages.pop(0)
                    logger.info(
                        f"Tokens {total_tokens}/{self.max_tokens}, pruning tool call & response: {removed_message}"
                    )
            else:
                # Remove just the oldest message
                removed_message = self.messages.pop(0)
                logger.info(f"Removed the following message to maintain token limit: {removed_message}")

            total_tokens = self._get_total_tokens()

        metadata = {
            "original_size": original_size,
            "final_size": len(self.messages),
            "total_tokens": total_tokens,
        }
        logger.debug(f"add_message metadata: {json.dumps(metadata, indent=4)}")

    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about the current context window."""
        total_tokens = self._get_total_tokens()
        return {
            "message_count": len(self.messages),
            "total_tokens": total_tokens,
            "remaining_tokens": self.max_tokens - total_tokens,
            "is_at_capacity": total_tokens >= self.max_tokens,
        }

    def clear_context(self) -> None:
        """Clear all messages from the context window."""
        self.messages.clear()
