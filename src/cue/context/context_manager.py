import json
import logging
from typing import Any, Dict, List, Union

from pydantic import BaseModel

from ..schemas import MessageParam, CompletionResponse, ToolResponseWrapper
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class DynamicContextManager:
    def __init__(self, max_tokens: int = 4096, batch_remove_percentage: float = 0.25):
        """
        Initialize the DynamicContextManager with a maximum token limit.

        Args:
            max_tokens (int): Maximum number of tokens to maintain in context
            batch_remove_percentage (float): Percentage of tokens to remove when limit is reached
        """
        self.max_tokens = max_tokens
        self.batch_remove_size = int(max_tokens * batch_remove_percentage)
        self.messages: List[Dict] = []
        self.token_counter = TokenCounter()
        # Track window stability for cache optimization
        self.last_removal_tokens = 0  # Track tokens at last removal
        self.messages_since_removal = 0  # Track messages added since last removal

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

    def add_message(
        self, message: Union[CompletionResponse, ToolResponseWrapper, MessageParam, Dict[str, Any], BaseModel]
    ) -> None:
        """Add a new message and manage the sliding window."""
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
        self.messages_since_removal += 1

        # Only remove when we exceed the limit
        if total_tokens > self.max_tokens:
            self._batch_remove_messages()
            total_tokens = self._get_total_tokens()

        metadata = {
            "original_size": original_size,
            "final_size": len(self.messages),
            "total_tokens": total_tokens,
            "messages_since_removal": self.messages_since_removal,
        }
        logger.debug(f"add_message metadata: {json.dumps(metadata, indent=4)}")

    def _has_tool_calls(self, msg: Dict) -> bool:
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

    def _is_tool_result(self, msg: Dict) -> bool:
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

    def _find_tool_sequence_indices(self, start_idx: int) -> set[int]:
        """
        Find all indices that belong to a tool sequence starting from a given index.
        Matches tool calls with their corresponding tool results using tool_call_id.
        """
        sequence_indices = set()
        if start_idx >= len(self.messages):
            return sequence_indices

        msg = self.messages[start_idx]
        if not self._has_tool_calls(msg):
            return sequence_indices

        sequence_indices.add(start_idx)
        tool_call_ids = set()

        # Collect all tool_call_ids from the tool calls message
        if msg.get("tool_calls"):
            for call in msg["tool_calls"]:
                logger.debug(f"Processing tool call: {call}")
                tool_call_ids.add(call["id"])
        elif isinstance(msg.get("content", []), list):
            for item in msg.get("content", []):
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_call_ids.add(item.get("id"))

        logger.debug(f"Collected tool_call_ids: {tool_call_ids}")

        # Find corresponding tool results
        remaining_ids = tool_call_ids.copy()
        for i in range(start_idx + 1, len(self.messages)):
            cur_msg = self.messages[i]
            if not self._is_tool_result(cur_msg):
                break

            tool_call_id = cur_msg.get("tool_call_id")
            logger.debug(f"Checking tool result with ID: {tool_call_id}, remaining IDs: {remaining_ids}")
            if tool_call_id in remaining_ids:
                sequence_indices.add(i)
                remaining_ids.remove(tool_call_id)
                logger.debug(f"Added index {i} to sequence, remaining IDs: {remaining_ids}")
                if not remaining_ids:  # All tool results found
                    break

        if remaining_ids:
            logger.warning(f"Not all tool results found. Missing IDs: {remaining_ids}")

        logger.debug(f"Final sequence indices: {sequence_indices}")
        return sequence_indices

    def _batch_remove_messages(self) -> None:
        """Remove a batch of oldest messages while preserving tool sequences."""
        if not self.messages:
            return

        total_tokens = self._get_total_tokens()
        tokens_to_remove = self.batch_remove_size  # Always remove the configured batch size

        logger.info(
            f"Starting batch removal - Total tokens: {total_tokens}, "
            f"To remove: {tokens_to_remove}, "
            f"Messages since last removal: {self.messages_since_removal}"
        )

        removed_tokens = 0
        messages_to_remove = 0

        # Keep checking messages from the start until we've removed enough tokens
        current_idx = 0
        while removed_tokens < tokens_to_remove and current_idx < len(self.messages):
            if self._has_tool_calls(self.messages[current_idx]):
                # Get all indices in this tool sequence using the existing method
                sequence_indices = self._find_tool_sequence_indices(current_idx)
                if not sequence_indices:
                    # No complete sequence found, move to next message
                    current_idx += 1
                    continue

                # Calculate tokens for the whole sequence
                sequence_tokens = sum(self._count_dict_tokens(self.messages[i]) for i in sequence_indices)

                # Remove the sequence if it fits in our budget
                if removed_tokens + sequence_tokens <= tokens_to_remove:
                    removed_tokens += sequence_tokens
                    # Keep track of the highest index we need to remove
                    messages_to_remove = max(messages_to_remove, max(sequence_indices) + 1)
                    logger.debug(
                        f"Including tool sequence in removal: indices {sequence_indices}, " f"tokens: {sequence_tokens}"
                    )

                # Move past this sequence
                current_idx = max(sequence_indices) + 1
            else:
                # Regular message
                msg_tokens = self._count_dict_tokens(self.messages[current_idx])
                if removed_tokens + msg_tokens <= tokens_to_remove:
                    removed_tokens += msg_tokens
                    messages_to_remove = current_idx + 1
                current_idx += 1

        # Remove messages from the start
        if messages_to_remove > 0:
            removed = self.messages[:messages_to_remove]
            self.messages = self.messages[messages_to_remove:]

            # Log removed messages
            for msg in removed:
                logger.info(
                    f"Removed message: role={msg.get('role')}, "
                    f"tool_call_id={msg.get('tool_call_id')}, "
                    f"tool_calls={msg.get('tool_calls')}"
                )

        # Update tracking
        self.last_removal_tokens = self._get_total_tokens()
        self.messages_since_removal = 0

        logger.info(
            f"Batch removal complete. Removed {removed_tokens} tokens, "
            f"messages: {messages_to_remove}, "
            f"remaining tokens: {self.last_removal_tokens}"
        )
