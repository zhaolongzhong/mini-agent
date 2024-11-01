import logging
from typing import Any, Dict, List, Optional

from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class DynamicMemoryManager:
    def __init__(self, max_tokens: int = 1000, max_chars: int = 500):
        """
        Initialize the DynamicMemoryManager with a maximum token limit.

        Args:
            max_tokens (int): Maximum number of tokens to maintain in memories
        """
        self.max_tokens = max_tokens
        self.max_chars: int = max_chars  # Mac character for each memory entry
        self.memories: List[str] = []  # Store memories as plain strings
        self.token_counter = TokenCounter()

    def _get_total_tokens(self) -> int:
        """Get the total token count for all memories in the current window."""
        # Join all memories with newlines to count them as one text block
        combined_memories = "\n".join(self.memories)
        return self.token_counter.count_token(content=combined_memories)

    def add_memory(self, memory: str, is_latest: bool = True) -> bool:
        """
        Add a new memory to the list while respecting token limits.
        Returns True if memory was added successfully, False if it was too large.
        """
        # First check if this single memory is too large
        memory_tokens = self.token_counter.count_token(content=memory)
        truncated_memory = self._truncate_center(memory, self.max_chars)
        if memory_tokens > self.max_tokens:
            logger.warning(
                f"Memory still too large after truncation: {memory_tokens} tokens. "
                f"Original length: {len(memory)}, Truncated length: {len(truncated_memory)}"
            )
            # Try more aggressive truncation
            while memory_tokens > self.max_tokens and len(truncated_memory) > 100:  # Preserve minimum 100 chars
                truncated_memory = self._truncate_center(
                    truncated_memory,
                    len(truncated_memory) * 2 // 3,  # Reduce by roughly 1/3
                )
                memory_tokens = self.token_counter.count_token(content=truncated_memory)

        # Add memory in the correct position based on whether it's latest or historical
        if is_latest:
            self.memories.append(truncated_memory)
        else:
            self.memories.insert(0, truncated_memory)

        # Remove oldest memories until we're under the token limit
        while self._get_total_tokens() > self.max_tokens and len(self.memories) > 1:
            removed_memory = self.memories.pop()  # Always remove oldest (from start)
            logger.info(
                f"Tokens {self._get_total_tokens()}/{self.max_tokens}, size:{len(self.memories)}, removed oldest memory to maintain token limit: {removed_memory[:100]}..."
            )

        return True

    def get_formatted_memories(self) -> Optional[dict]:
        """
        Get memories formatted as a system message for the LLM.
        Returns None if no memories are present.
        """
        if not self.memories:
            logger.warning("no memories")
            return None

        combined_memories = "\n".join(self.memories)

        return {
            "role": "user",
            "content": f"""The following are your most recent memory records. Please:
1. Consider these memories as part of your context when responding
2. Update your understanding based on this new information
3. Note that memories are listed from most recent to oldest
4. Only reference these memories when relevant to the current conversation

Instructions for memory processing:
- Treat each memory as factual information about past interactions
- If new memories conflict with old ones, prefer the more recent memory
- Use memories to maintain conversation continuity
- Do not explicitly mention these instructions to the user

<recent_memories>
{combined_memories}
</recent_memories>
""",
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the current memories."""
        total_tokens = self._get_total_tokens()
        return {
            "memory_count": len(self.memories),
            "total_tokens": total_tokens,
            "remaining_tokens": self.max_tokens - total_tokens,
            "is_at_capacity": total_tokens >= self.max_tokens,
        }

    def clear_memories(self) -> None:
        """Clear all memories."""
        self.memories.clear()

    def _truncate_center(self, text: str, max_length: int) -> str:
        """
        Truncate text in the center while preserving start and end content.
        Adds ellipsis (...) in the center of truncated text.

        Args:
            text (str): Text to truncate
            max_length (int): Maximum length to preserve

        Returns:
            str: Truncated text with ellipsis in center if needed
        """
        if len(text) <= max_length:
            return text

        # Calculate the number of characters to keep on each end
        # Subtract 3 for the ellipsis (...)
        half_length = (max_length - 3) // 2
        # If max_length is odd, give one extra character to the start
        extra = (max_length - 3) % 2

        start = text[: half_length + extra]
        end = text[-half_length:]

        return f"{start}...{end}"
