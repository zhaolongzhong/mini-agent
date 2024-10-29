import asyncio

from cue import ChatModel, AgentConfig, AsyncCueClient


async def main():
    api_key = "sk-.."
    client = AsyncCueClient(
        config=AgentConfig(
            api_key=api_key,
            model=ChatModel.GPT_4O_MINI,
        )
    )

    try:
        await client.initialize()
        response = await client.send_message("Hello, there!")
        print(f"{response}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
