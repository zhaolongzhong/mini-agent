from chat_completion import send_completion_request
from message import Message

messages = [Message(role="system", content="You are a helpful assistant.")]


def send_prompt(content: str):
    messages.append(Message(role="user", content=content))
    return send_completion_request(messages)


def main():
    while True:
        user_input = input("[User ]: ")
        response = send_prompt(user_input)
        message = Message(**response.choices[0].message.model_dump())
        print(f"[Agent]: {message.content}")


if __name__ == "__main__":
    main()
