from pydantic import BaseModel, field_validator


class ToolMessage(BaseModel):
    content: str
    """The content of the tool message."""
    role: str = "tool"
    tool_call_id: str
    """Tool call that this message is responding to."""

    @field_validator("role", mode="before")
    def validate_role(cls, value):
        if value not in ["tool"]:
            raise ValueError('Role must be "tool"')
        return value
