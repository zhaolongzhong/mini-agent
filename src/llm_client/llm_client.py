import os

from llm_client.anthropic_client import AnthropicClient
from llm_client.gemini_client import GeminiClient
from llm_client.groq_client import GroqClient
from llm_client.llm_request import LLMRequest
from llm_client.openai_client import OpenAIClient
from llm_client.together_client import TogetherAIClient
from memory.memory import MemoryInterface
from schemas.agent import AgentConfig
from schemas.request_metadata import Metadata
from utils.logs import logger


class LLMClient(LLMRequest):
    def __init__(self, config: AgentConfig):
        self.llm_client: LLMRequest = self._initialize_client(config)

    def _initialize_client(self, config: AgentConfig):
        model = config.model
        api_key = os.getenv(model.api_key_env)
        if not api_key and model.api_key_env != "GOOGLE_API_KEY":
            logger.error(f"API key for {model.api_key_env} not found in environment variables")
            raise ValueError(f"API key for {model.api_key_env} not found")

        client_class_mapping = {
            "openai": OpenAIClient,
            "anthropic": AnthropicClient,
            "groq": GroqClient,
            "together": TogetherAIClient,
            "google": GeminiClient,
        }

        client_class = client_class_mapping.get(model.key_prefix)
        if not client_class:
            logger.error(f"Client class for key prefix {model.key_prefix} not found")
            raise ValueError(f"Client class for key prefix {model.key_prefix} not found")

        return client_class(api_key=api_key, config=config)

    async def send_completion_request(self, memory: MemoryInterface, metadata: Metadata) -> dict:
        return await self.llm_client.send_completion_request(memory=memory, metadata=metadata)
