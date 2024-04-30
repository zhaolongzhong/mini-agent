import asyncio
import itertools
import sys

from chat_completion import send_completion_request
from models.message import Message
from planning.planning import make_plan
from utils.console import clear_line
from utils.logs import log

messages = [Message(role="system", content="You are a helpful assistant.")]


async def send_prompt(content: str):
    messages.append(Message(role="user", content=content))
    response = await make_plan(content)
    if response:
        log.debug(f"Planning] response: {response.choices[0].message}")
    return await send_completion_request(messages=messages)


async def progress_indicator():
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    try:
        while True:
            sys.stdout.write(f"\r{next(spinner)}")  # Print the spinner character
            sys.stdout.flush()
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        clear_line()


async def main():
    while True:
        user_input = input("[User ]: ")
        if user_input:
            indicator = asyncio.create_task(progress_indicator())
            try:
                response = await send_prompt(user_input)
                indicator.cancel()
                log.debug(f"[main] {response.choices[0].message}")
                message = Message(**response.choices[0].message.model_dump())
                print(f"[Agent]: {message.content}")
            finally:
                try:
                    await indicator
                except asyncio.CancelledError:
                    sys.stdout.write("\r")
                    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
