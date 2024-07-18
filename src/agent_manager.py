import asyncio
import sys
from datetime import datetime

from agent import Agent
from llm_client.llm_model import ChatModel
from memory.memory import StorageType
from schemas.agent import AgentConfig
from schemas.error import ErrorResponse
from schemas.request_metadata import Metadata
from tools.tool_manager import Tool
from utils.cli_utils import progress_indicator
from utils.logs import logger


class AgentManager:
    def __init__(
        self,
        env=None,
        input_func=input,
        is_test=False,
    ):
        logger.info("AgentManager initialized")
        self.agents = {}
        self.input_func = input_func
        self.is_test = is_test

    async def create_agents(self, model=ChatModel.GPT_4O_MINI):
        # id = "main_test" if self.is_test else "main"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        id = f"main_test_{timestamp}" if self.is_test else "main"
        self.agent: Agent = await self.create_agent(
            id=id,
            name="MainAgent",
            storage_type=StorageType.FILE,
            model=model,  # Try different models here
            tools=[
                Tool.FileRead,
                Tool.FileWrite,
                Tool.CheckFolder,
                Tool.CodeInterpreter,
                Tool.ShellTool,
                Tool.MakePlan,
                Tool.BrowseWeb,
                Tool.ManageEmail,
                Tool.ManageDrive,
            ],
        )

    async def create_agent(
        self,
        id: str = "",
        name: str = "",
        model: ChatModel = ChatModel.GPT_4O,
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

    async def handle_input(self, user_input: str):
        if user_input:
            indicator = None
            if self.is_test is False:
                indicator = asyncio.create_task(progress_indicator())
            try:
                response = await self.agent.send_prompt(user_input)
                if indicator:
                    indicator.cancel()
                logger.debug(f"[main] {response}")
                if isinstance(response, ErrorResponse):
                    return f"[Agent]: There is an error. Error: {response.model_dump_json()}"
                else:
                    return f"[Agent]: {response.content}"
            finally:
                if indicator:
                    try:
                        await indicator
                    except asyncio.CancelledError:
                        sys.stdout.write("\r")
                        sys.stdout.flush()
        return None

    def get_metadata(self) -> Metadata | None:
        if self.agent is None:
            return None
        return self.agent.metadata

    async def run(self):
        logger.info("AgentManager run")
        await self.create_agents()
        while True:
            user_input = self.input_func("[User ]: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            response = await self.handle_input(user_input)
            if response:
                logger.debug(f"metadata: {self.get_metadata()}")
                print(response)


async def main():
    agentManager = AgentManager()
    await agentManager.run()


if __name__ == "__main__":
    asyncio.run(main())
