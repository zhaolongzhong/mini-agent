from pydantic import BaseModel, field_validator


class MessageBase(BaseModel):
    content: str
    role: str
    name: str | None = None
    """An optional name for the participant.

    Provides the model information to differentiate between participants of the same
    role.
    """

    @field_validator("role", mode="before")
    def check_role(cls, value):
        if value not in ["user", "system"]:
            raise ValueError('Role must be either "user" and "system"')
        return value


class Message(MessageBase):
    pass


def toChatCompletionMessage(chat_completion_message: any) -> Message:
    """
    Convert choices[0].message to local ChatCompletionMessage object
    """
    if chat_completion_message:
        message_dict = (
            chat_completion_message.model_dump()
            if isinstance(chat_completion_message, BaseModel)
            else chat_completion_message
        )
        try:
            return Message(**message_dict)
        except Exception as e:
            print(f"parse error. {e}")
    else:
        print(f"chat_completion_message :\n{chat_completion_message}")
