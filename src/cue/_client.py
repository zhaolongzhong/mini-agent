import asyncio
from typing import Optional

from ._agent_manager import AgentManager
from .llm import ChatModel
from .schemas import AgentConfig, CompletionResponse
from .tools._tool import Tool
from .utils.logs import _logger, setup_logging

setup_logging()


class AsyncCueClient:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.logger = _logger
        self.config = config
        self.agent_config = self._create_agent_config(config)
        self.agent_manager = AgentManager()

    def _create_agent_config(self, config: Optional[AgentConfig] = None) -> AgentConfig:
        default_config = AgentConfig(
            id="cue_async_client",
            name="cue_async_client",
            model=ChatModel.GPT_4O_MINI,
            temperature=0.8,
            max_tokens=2000,
            conversation_id="",
            tools=[
                Tool.FileRead,
                Tool.FileWrite,
                Tool.ShellTool,
            ],
        )

        if config:
            updated_config = default_config.model_dump()
            updated_config.update(config.model_dump(exclude_unset=True))
            return AgentConfig(**updated_config)

        return default_config

    async def initialize(self):
        self.logger.info("Initializing AsyncCueClient")
        self.agent_manager.register_agent(self.agent_config)

    async def send_message(self, message: str) -> str:
        self.logger.debug(f"Sending message: {message}")
        response = await self.agent_manager.run(self.agent_config.name, message)

        if isinstance(response, CompletionResponse):
            return response.get_text()
        return str(response)

    async def cleanup(self):
        self.logger.info("Cleaning up AsyncCueClient")
        await self.agent_manager.clean_up()


async def main():
    client = AsyncCueClient()
    await client.initialize()

    try:
        response = await client.send_message("Hello, Cue!")
        print(f"Cue: {response}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
