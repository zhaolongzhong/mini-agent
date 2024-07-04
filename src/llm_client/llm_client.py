import os

from llm_client.anthropic import AnthropicClient
from llm_client.llm_model import ChatModel
from llm_client.llm_request import LLMRequest
from llm_client.openai_client import OpenAIClient
from memory.memory import MemoryInterface
from schemas.request_metadata import Metadata
from tools.tool_manager import ToolManager
from utils.logs import logger


class LLMClient(LLMRequest):
    def __init__(
        self,
        model: str = ChatModel.GPT_4O.value,
        tool_manager: ToolManager | None = None,
    ):
        self.tool_manager = tool_manager
        if model == ChatModel.GPT_4O.value:
            api_key = os.getenv("OPENAI_API_KEY")
            self.llm_client = OpenAIClient(api_key=api_key, model=model, tool_manager=self.tool_manager)
        elif model == ChatModel.CLAUDE_3_5_SONNET_20240620.value:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            self.llm_client = AnthropicClient(api_key=api_key, model=model, tool_manager=tool_manager)
        else:
            logger.error(f"Model {model} not supported")
            raise ValueError(f"Model {model} not supported")

    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ) -> dict:
        return await self.llm_client.send_completion_request(memory=memory, metadata=metadata)
