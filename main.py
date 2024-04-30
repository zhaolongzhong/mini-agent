from chat_completion import send_completion_request
from models.message import Message
from planning.planning import make_plan

from utils.logs import logger as log

messages = [Message(role="system", content="You are a helpful assistant.")]


def send_prompt(content: str):
    messages.append(Message(role="user", content=content))
    response = make_plan(content)
    if response:
        log.debug(f"[Planning] response: {response.choices[0].message}")
    return send_completion_request(messages=messages)


def main():
    while True:
        user_input = input("[User ]: ")
        response = send_prompt(user_input)
        log.debug(response.choices[0].message)
        message = Message(**response.choices[0].message.model_dump())
        print(f"[Agent]: {message.content}")


if __name__ == "__main__":
    main()
