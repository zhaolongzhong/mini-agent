from chat_completion import send_completion_request
from models.message import Message
from tools.available_tools import tools_list
from utils.logs import logger as log

messages = [Message(role="system", content="You are a helpful assistant.")]


def send_prompt(content: str):
    messages.append(Message(role="user", content=content))
    return send_completion_request(messages, tools_list)


def main():
    while True:
        user_input = input("[User ]: ")
        response = send_prompt(user_input)
        log.debug(response.choices[0].message)
        message = Message(**response.choices[0].message.model_dump())
        print(f"[Agent]: {message.content}")


if __name__ == "__main__":
    main()
