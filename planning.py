from core.chat_base import ChatBase
from models.message import Message
from tools.available_tools import tools_list
from utils.logs import logger as log

chat_base = ChatBase(tools=tools_list)


def evaluate_input(content: str):
    messages = [
        Message(
            role="system",
            content="You are are helpful assistant to help evaluate if the user request needs a plan based on the complexity of the task and problems. If it is accomplished by available tools, then response no. Please only respond with Yes or No.",
        )
    ]
    messages.append(
        Message(
            role="assistant", content="Here is the task (problem or request):" + content
        )
    )
    return chat_base.send_request(messages, use_tools=True)


def make_plan(content: str):
    response = evaluate_input(content)
    chat_completion_message = response.choices[0].message
    log.debug(f"[Planning] evaluation response: {chat_completion_message}")
    if (
        chat_completion_message.content is not None
        and "yes" in chat_completion_message.content.lower()
    ):
        messages = [
            Message(
                role="system",
                content="You are are helpful assistant to make a plan for a task or user request. Please provide a plan in the next few sentences.",
            )
        ]
        messages.append(
            Message(
                role="assistant", content="Make a plan for the user request: " + content
            )
        )
        return chat_base.send_request(messages)
