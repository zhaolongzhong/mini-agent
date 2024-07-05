import asyncio
import sys

from agent import Agent
from llm_client.llm_model import ChatModel
from memory.memory import StorageType
from schemas.agent import AgentConfig
from schemas.error import ErrorResponse
from tools.tool_manager import Tool
from utils.cli_utils import progress_indicator
from utils.logs import logger


class AgentManager:
    def __init__(self, env=None):
        logger.info("AgentManager initialized")
        self.agents = {}

    async def create_agents(self):
        self.agent: Agent = await self.create_agent(
            id="main",
            name="MainAgent",
            storage_type=StorageType.FILE,
            model=ChatModel.GPT_4O.value,
            tools=[
                Tool.FileRead,
                Tool.FileWrite,
                Tool.CheckFolder,
                Tool.CodeInterpreter,
                Tool.ShellTool,
            ],
        )

    async def create_agent(
        self,
        id: str = "",
        name: str = "",
        model: str = ChatModel.GPT_4O.value,
        storage_type: StorageType = StorageType.FILE,
        tools: list[Tool] = [],
    ):
        if id in self.agents:
            logger.warning(f"Agent with id {id} already exists, return existing agent.")
            return self.agents[id]
        agent = await Agent.create(
            config=AgentConfig(
                id=id,
                name=name,
                storage_type=storage_type,
                model=model,
                tools=tools,
            ),
        )
        self.agents[agent.id] = agent
        logger.info(f"Created agent, available agents: {list(self.agents.keys())}")
        return agent

    async def start(self):
        logger.info("AgentManager start")
        await self.create_agents()
        await self.run_main_agent()

    async def run_main_agent(self):
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
