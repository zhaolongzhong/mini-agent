import json
import logging
from typing import Any, Union, Optional

from pydantic import BaseModel

from ..utils import DebugUtils, TokenCounter
from ..schemas import MessageParam, CompletionResponse, ToolResponseWrapper
from .._agent_summarizer import ContentSummarizer
from ..utils.mesage_params_utils import has_tool_calls, is_tool_result

logger = logging.getLogger(__name__)


class DynamicContextManager:
    def __init__(
        self,
        model: str,
        max_tokens: int = 4096,
        batch_remove_percentage: float = 0.30,
        summarizer: Optional[ContentSummarizer] = None,
    ):
        """
        Initialize the DynamicContextManager with a maximum token limit.

        Args:
            model (str): LLM model id
            max_tokens (int): Maximum number of tokens to maintain in context
            batch_remove_percentage (float): Percentage of tokens to remove when limit is reached
            summarizer (ContentSummarizer): Summarize messages
        """
        self.model = model
        self.max_tokens = max_tokens
        self.batch_remove_percentage = batch_remove_percentage
        self.messages: list[dict] = []
        self.summaries: list[str] = []
        self.token_counter = TokenCounter()
        self.summarizer = summarizer
        # Track window stability for cache optimization
        self.last_removal_tokens = 0  # Track tokens at last removal
        self.messages_since_removal = 0  # Track messages added since last removal
        self.summaries_content: Optional[str] = None

    def _get_batch_remove_size(self) -> int:
        total = self._get_total_tokens()
        extra_remove_size = 0
        if total > self.max_tokens:
            extra_remove_size = total - self.max_tokens
        batch_remove_size = int(self.max_tokens * self.batch_remove_percentage) + extra_remove_size
        return batch_remove_size

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

    def get_context_stats(self) -> dict[str, Any]:
        """Get statistics about the current context window."""
        total_tokens = self._get_total_tokens()
        return {
            "message_count": len(self.messages),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "remaining_tokens": self.max_tokens - total_tokens,
            "is_at_capacity": total_tokens >= self.max_tokens,
        }

    def _update_summaries_content(self):
        if not self.summaries:
            return
        # Take only the last few summaries if we have more
        recent_summaries = self.summaries[-6:] if len(self.summaries) > 6 else self.summaries

        numbered_summaries = [f"{i + 1}. {summary.strip()}" for i, summary in enumerate(recent_summaries) if summary]

        contents = "\n".join(numbered_summaries)
        self.summaries_content = contents

    def get_summaries(self) -> Optional[str]:
        if not self.summaries_content:
            return None
        return f"Here is summaries of truncated old messages <summaries>{self.summaries_content}</summaries>"

    def get_messages(self) -> list[dict]:
        messages = self.messages.copy()
        return messages

    def clear_context(self) -> None:
        """Clear all messages from the context window."""
        self.messages.clear()

    async def add_messages(
        self,
        new_messages: list[Union[CompletionResponse, ToolResponseWrapper, MessageParam, dict[str, Any], BaseModel]],
    ) -> bool:
        """Add new messages to the conversation history and manage the sliding window token limit.

        This method handles the addition of new messages while maintaining the conversation
        within the specified token limit. If the token limit is exceeded, older messages
        may be removed and optionally summarized.

        Args:
            new_messages: A list of messages to add. Can contain CompletionResponse,
                ToolResponseWrapper, MessageParam, dict, or BaseModel instances.

        Returns:
            bool: True if any messages were removed due to token limit management,
                False if all messages were retained.

        Raises:
            Exception: If an unsupported message type is provided.
        """
        original_size = len(self.messages)
        for message in new_messages:
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
            self.messages_since_removal += 1

        total_tokens = self._get_total_tokens()
        original_tokens = total_tokens

        has_truncated = False
        # Only remove when we exceed the limit
        if total_tokens > self.max_tokens:
            orignal_len = len(self.messages)
            DebugUtils.take_snapshot(messages=self.messages, suffix="batch_remove_before", subfolder="batch_remove")
            removed_messages = self._batch_remove_messages()
            DebugUtils.take_snapshot(messages=self.messages, suffix="batch_remove_after", subfolder="batch_remove")

            new_len = len(self.messages)
            has_truncated = len(removed_messages) > 0
            total_tokens = self._get_total_tokens()
            if not has_truncated:
                logger.error(
                    f"Reach max tokens, but not remove any messages, orignal_len: {orignal_len}, new_len:{new_len}"
                )
            if self.summarizer and has_truncated:
                logger.debug(
                    f"Summarize removed messages: {len(removed_messages)}, new stats: {self.get_context_stats()}"
                )
                summary = await self.summarizer.summarize(self.model, removed_messages)
                self.summaries.append(summary)

        metadata = {
            "max_token": self.max_tokens,
            "original_size": original_size,
            "final_size": len(self.messages),
            "original_tokens": original_tokens,
            "new_total_tokens": total_tokens,
            "messages_since_removal": self.messages_since_removal,
            "has_truncated": has_truncated,
        }
        logger.debug(f"add_messages result: {json.dumps(metadata, indent=4)}")
        self._update_summaries_content()
        return has_truncated

    def _find_tool_sequence_indices(self, start_idx: int) -> set[int]:
        """
        Find all indices that belong to a tool sequence starting from a given index.
        Matches tool calls with their corresponding tool results using tool_call_id.
        """
        sequence_indices = set()
        if start_idx >= len(self.messages):
            return sequence_indices

        msg = self.messages[start_idx]
        if not has_tool_calls(msg):
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
            if not is_tool_result(cur_msg):
                break

            tool_ids = []
            tool_call_id = cur_msg.get("tool_call_id")
            if tool_call_id:
                tool_ids.append(tool_call_id)
            elif isinstance(cur_msg.get("content", []), list):
                for tool_result in cur_msg.get("content", []):
                    if isinstance(tool_result, dict) and tool_result.get("type") == "tool_result":
                        id = tool_result.get("tool_use_id")
                        tool_ids.append(id)
                    else:
                        logger.error(f"Content has unexpected type: {tool_result}")
            else:
                logger.error(f"Unexpected type: {cur_msg}")

            logger.debug(f"Checking tool result with ID: {tool_ids}, remaining IDs: {remaining_ids}")
            for tool_id in tool_ids:
                if tool_id in remaining_ids:
                    sequence_indices.add(i)
                    remaining_ids.remove(tool_id)
                    logger.debug(f"Added index {i} to sequence, remaining IDs: {remaining_ids}")
                    if not remaining_ids:  # All tool results found
                        break

        if remaining_ids:
            logger.warning(f"Not all tool results found. Missing IDs: {remaining_ids}")

        logger.debug(f"Final sequence indices: {sequence_indices}")
        return sequence_indices

    def _batch_remove_messages(self) -> list[Any]:
        if not self.messages:
            return []

        tokens_to_remove = self._get_batch_remove_size()
        message_tokens = {}
        removed_tokens = 0
        messages_to_remove = 0
        current_idx = 0

        def get_message_tokens(idx):
            if idx not in message_tokens:
                message_tokens[idx] = self._count_dict_tokens(self.messages[idx])
            return message_tokens[idx]

        while removed_tokens < tokens_to_remove and current_idx < len(self.messages):
            if has_tool_calls(self.messages[current_idx]):
                sequence_indices = self._find_tool_sequence_indices(current_idx)
                if not sequence_indices:
                    current_idx += 1
                    continue

                sequence_tokens = sum(get_message_tokens(i) for i in sequence_indices)

                # Check if adding sequence would exceed target by too much
                if removed_tokens + sequence_tokens > tokens_to_remove:
                    excess = (removed_tokens + sequence_tokens) - tokens_to_remove
                    metrics = {
                        "tokens_to_remove": tokens_to_remove,
                        "sequence_tokens": sequence_tokens,
                        "removed_tokens": removed_tokens,
                        "excess": excess,
                        "messages_to_remove": messages_to_remove,
                    }
                    logger.debug(f"About to remove extra tokens: {json.dumps(metrics, indent=4)}")
                    if excess > tokens_to_remove * 0.25:  # 25% threshold
                        break

                removed_tokens += sequence_tokens
                max_sequence_idx = max(sequence_indices)
                messages_to_remove = max(messages_to_remove, max_sequence_idx + 1)
                current_idx = max_sequence_idx + 1

            else:
                msg_tokens = get_message_tokens(current_idx)
                removed_tokens += msg_tokens
                messages_to_remove = current_idx + 1
                current_idx += 1

        # Remove messages and update tracking
        logger.debug(f"messages_to_remove: {messages_to_remove}, removed_tokens: {removed_tokens}")
        removed = self.messages[:messages_to_remove]
        self.messages = self.messages[messages_to_remove:]
        self.last_removal_tokens = self._get_total_tokens()
        self.messages_since_removal = 0

        return removed
