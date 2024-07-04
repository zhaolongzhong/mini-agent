import asyncio
import sys

from agent import Agent
from llm_client.llm_model import ChatModel
from memory.memory import StorageType
from schemas.agent import AgentConfig
from schemas.error import ErrorResponse
from tools.tool_manager import ToolManager
from utils.cli_utils import progress_indicator
from utils.logs import logger


class AgentManager:
    def __init__(self, env=None):
        self.tools_manager = ToolManager()

    async def create_agent(self):
        self.agent = await Agent.create(
            config=AgentConfig(
                id="1",
                name="Main Agent",
                storage_type=StorageType.FILE,
                model=ChatModel.GPT_4O.value,
                # model=ChatModel.CLAUDE_3_5_SONNET_20240620.value,
            ),
            tools_manager=self.tools_manager,
        )

    async def start(self):
        await self.create_agent()
        await self.run()

    async def run(self):
        while True:
            user_input = input("[User ]: ")
            if user_input:
                indicator = asyncio.create_task(progress_indicator())
                try:
                    response = await self.agent.send_prompt(user_input)
                    indicator.cancel()
                    logger.debug(f"[main] {response}")
                    if isinstance(response, ErrorResponse):
                        print(f"[Agent]: There is an error. Error: {response.model_dump_json()}")
                    else:
                        print(f"[Agent]: {response.content}")
                finally:
                    try:
                        await indicator
                    except asyncio.CancelledError:
                        sys.stdout.write("\r")
                        sys.stdout.flush()


async def main():
    agentManager = AgentManager()
    await agentManager.start()


if __name__ == "__main__":
    asyncio.run(main())
