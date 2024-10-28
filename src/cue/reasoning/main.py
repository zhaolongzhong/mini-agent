import asyncio

from .reasoning_system import ReasoningCore

prompt = """

"""


async def main():
    reasoning = ReasoningCore()

    result = await reasoning.reasoning(prompt)
    print(f"final result: \n{result}")


if __name__ == "__main__":
    asyncio.run(main())


"""
# Run guide
export OPENAI_API_KEY=sk-
source .venv/bin/activate
python -m src.cue.reasoning.main
"""
