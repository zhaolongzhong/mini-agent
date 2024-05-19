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
