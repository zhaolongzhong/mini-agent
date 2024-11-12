import logging
from typing import Optional

from .llm.llm_client import LLMClient
from .schemas.agent_config import AgentConfig
from .utils.mesage_params_utils import get_text_from_message_params
from .schemas.completion_request import CompletionRequest

logger = logging.getLogger(__name__)


class ContentSummarizer:
    def __init__(self, config: AgentConfig):
        self.model = config.model
        self.client: LLMClient = LLMClient(config)
        self.tag = self.__class__.__name__

    async def summarize(self, model: str, messages: list[dict], instruction: Optional[str] = None) -> Optional[str]:
        """Summarize message content using LLM with optional custom instruction.

        Args:
            model: The model identifier to use
            messages: List of message dictionaries to summarize
            instruction: Optional custom instruction to append to the default summarization prompt

        Returns:
            Optional[str]: Summarized content or None if summarization fails
        """
        message_content = get_text_from_message_params(model=model, messages=messages, content_max_length=200)
        return await self._summarize_content(message_content, instruction)

    async def summarize_text(self, text: str, instruction: Optional[str] = None) -> Optional[str]:
        """Summarize arbitrary text content using LLM with optional custom instruction.

        Args:
            text: The text content to summarize
            instruction: Optional custom instruction to append to the default summarization prompt

        Returns:
            Optional[str]: Summarized content or None if summarization fails
        """
        return await self._summarize_content(text, instruction)

    async def _summarize_content(self, content: str, instruction: Optional[str] = None) -> Optional[str]:
        """Internal method to handle the actual summarization for both messages and text.

        Args:
            content: The content to summarize
            instruction: Optional custom instruction to append to the default summarization prompt

        Returns:
            Optional[str]: Summarized content or None if summarization fails
        """
        # Build the prompt with default instruction and optional custom instruction
        base_instruction = "Please summarize those content. Be specific on details and be concise."
        final_instruction = f"{base_instruction} {instruction}" if instruction else base_instruction

        message = {
            "role": "user",
            "content": f"<content>{content}</content> {final_instruction}",
        }

        request = CompletionRequest(
            model=self.model,
            messages=[message],
            temperature=0.4,
        )

        try:
            completion_response = await self.client.send_completion_request(request=request)
            return completion_response.get_text()
        except Exception as e:
            logger.error(f"{self.tag} error: {str(e)}")
            return None
