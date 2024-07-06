import asyncio

from agent import Agent
from llm_client.llm_model import ChatModel
from memory.memory import InMemoryStorage, StorageType
from schemas.agent import AgentConfig
from schemas.message import Message
from utils.logs import logger


async def make_plan(content: str):
    messages = [
        Message(
            role="system",
            content="You are are helpful assistant to make a plan for a task or user request. Please provide a plan in the next few sentences.",
        )
    ]
    # If use claude, first message must use the \"user\"
    messages.append(Message(role="user", content="User request: " + content))
    memory = InMemoryStorage()
    await memory.saveList(messages)
    agent = await Agent.create(
        config=AgentConfig(
            id="plan_agent",
            name="plan_agent",
            storage_type=StorageType.IN_MEMORY,
            model=ChatModel.GPT_4O,
        ),
    )
    return await agent.send_request(memory=memory)


async def main():
    result = await make_plan("Can you help to scaffold a new project using python?")
    logger.info(result)


if __name__ == "__main__":
    asyncio.run(main())
