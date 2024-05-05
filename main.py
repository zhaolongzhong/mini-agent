import asyncio
import itertools
import sys

from chat_completion import send_completion_request
from models.error import ErrorResponse
from models.message import Message
from planning.planning import make_plan
from utils.console import clear_line
from utils.logs import log

messages = [Message(role="system", content="You are a helpful assistant.")]


async def send_prompt(content: str):
    messages.append(Message(role="user", content=content))
    # response = await make_plan(content)
    # if response and not isinstance(response, ErrorResponse):
    #     log.debug(f"Planning] response: {response.choices[0].message}")
    response = await send_completion_request(messages=messages)
    if isinstance(response, ErrorResponse):
        return response
    else:
        message = Message(**response.choices[0].message.model_dump())
        messages.append(message)
        return message


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
                log.debug(f"[main] {response}")
                if isinstance(response, ErrorResponse):
                    print(
                        f"[Agent]: There is an error. Error: {response.model_dump_json()}"
                    )
                else:
                    print(f"[Agent]: {response.content}")
            finally:
                try:
                    await indicator
                except asyncio.CancelledError:
                    sys.stdout.write("\r")
                    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
