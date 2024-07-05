import os

from llm_client.anthropic_client import AnthropicClient
from llm_client.llm_request import LLMRequest
from llm_client.openai_client import OpenAIClient
from memory.memory import MemoryInterface
from schemas.agent import AgentConfig
from schemas.request_metadata import Metadata
from utils.logs import logger


class LLMClient(LLMRequest):
    def __init__(
        self,
        config: AgentConfig,
    ):
        if "gpt-4" in config.model:
            api_key = os.getenv("OPENAI_API_KEY")
            self.llm_client = OpenAIClient(api_key=api_key, config=config)
        elif "claude" in config.model:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            self.llm_client = AnthropicClient(api_key=api_key, config=config)
        else:
            logger.error(f"Model {config.model} not supported")
            raise ValueError(f"Model {config.model} not supported")

    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ) -> dict:
        return await self.llm_client.send_completion_request(memory=memory, metadata=metadata)
