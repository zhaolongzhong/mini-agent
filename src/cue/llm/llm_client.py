import logging

from ..memory.memory import MemoryInterface
from ..schemas.agent_config import AgentConfig
from ..schemas.request_metadata import Metadata
from .anthropic_client import AnthropicClient
from .gemini_client import GeminiClient
from .llm_request import LLMRequest
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class LLMClient(LLMRequest):
    def __init__(self, config: AgentConfig):
        self.llm_client: LLMRequest = self._initialize_client(config)

    def _initialize_client(self, config: AgentConfig):
        model = config.model
        client_class_mapping = {
            "openai": OpenAIClient,
            "anthropic": AnthropicClient,
            "google": GeminiClient,
        }

        client_class = client_class_mapping.get(model.key_prefix)
        if not client_class:
            logger.error(f"Client class for key prefix {model.key_prefix} not found")
            raise ValueError(f"Client class for key prefix {model.key_prefix} not found")

        return client_class(config=config)

    async def send_completion_request(self, memory: MemoryInterface, metadata: Metadata) -> dict:
        return await self.llm_client.send_completion_request(memory=memory, metadata=metadata)