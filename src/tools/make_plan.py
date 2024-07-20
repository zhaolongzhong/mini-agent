import asyncio
import os

import openai
from llm_client.llm_model import ChatModel
from schemas.message import Message
from utils.logs import logger


def create_client() -> openai.OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(
        api_key=api_key,
    )
    return client


async def make_plan(content: str):
    messages = [
        Message(
            role="system",
            content="You are are helpful assistant to make a plan for a task or user request. Please provide a plan in the next few sentences.",
        )
    ]
    # If use claude, first message must use the \"user\"
    messages.append(Message(role="user", content=content))

    client = create_client()
    chat_completion = client.chat.completions.create(
        model=ChatModel.GPT_4O.model_id(),
        messages=[item.model_dump() for item in messages],
        temperature=0,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    content = chat_completion.choices[0].message.content
    logger.info(f"make_plan: {content}")
    return content


async def main():
    result = await make_plan("Can you help to scaffold a new project using python?")
    logger.info(result)


if __name__ == "__main__":
    asyncio.run(main())
