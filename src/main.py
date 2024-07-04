import asyncio
import sys

from chat_completion import send_completion_request
from memory.memory import FileStorage, InMemoryStorage, MemoryInterface
from schemas.error import ErrorResponse
from schemas.message import Message
from schemas.request_metadata import Metadata
from schemas.tool_call import AssistantMessage
from utils.cli_utils import progress_indicator
from utils.logs import logger

use_local_storage = True


async def send_prompt(memory: MemoryInterface, content: str):
    await memory.save(Message(role="user", content=content))
    response = await send_completion_request(memory=memory, metadata=Metadata(last_user_message=content))
    if isinstance(response, ErrorResponse):
        return response
    else:
        message = AssistantMessage(**response.choices[0].message.model_dump())
        return message


async def main():
    if use_local_storage:
        logger.debug("Using local storage")
        memory = FileStorage()
    else:
        logger.debug("Using in memory storage")
        memory = InMemoryStorage()

    await memory.init_messages()

    while True:
        user_input = input("[User ]: ")
        if user_input:
            indicator = asyncio.create_task(progress_indicator())
            try:
                response = await send_prompt(memory, user_input)
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


if __name__ == "__main__":
    asyncio.run(main())
