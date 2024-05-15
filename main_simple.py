import asyncio
import sys

from chat_completion import send_completion_request_simple
from models.error import ErrorResponse
from models.message import Message
from models.message_param import MessageLike
from models.request_metadata import Metadata
from models.tool_call import AssistantMessage
from utils.cli_utils import progress_indicator
from utils.logs import log


async def send_prompt(messages: list[MessageLike], content: str):
    messages.append(Message(role="user", content=content))
    # response = await make_plan(content)
    # if response and not isinstance(response, ErrorResponse):
    #     log.debug(f"Planning] response: {response.choices[0].message}")
    response = await send_completion_request_simple(
        messages=messages, metadata=Metadata(last_user_message=content)
    )
    if isinstance(response, ErrorResponse):
        return response
    else:
        message = AssistantMessage(**response.choices[0].message.model_dump())
        messages.append(message)
        return message


async def main():
    messages = [Message(role="system", content="You are a helpful assistant.")]

    while True:
        user_input = input("[User ]: ")
        if user_input:
            indicator = asyncio.create_task(progress_indicator())
            try:
                response = await send_prompt(messages, user_input)
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
