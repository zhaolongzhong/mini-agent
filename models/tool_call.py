from pydantic import BaseModel, validator


class Function(BaseModel):
    arguments: str
    name: str


class ToolCall(BaseModel):
    id: str
    function: Function | dict
    type: str

    @validator("function", pre=True)
    @classmethod
    def ensure_function_dict(cls, v):
        return v if isinstance(v, dict) else v.dict()


class ToolCallMessage(BaseModel):
    content: str | None = None
    role: str
    tool_calls: list[ToolCall]


class ToolResponseMessage(BaseModel):
    tool_call_id: str
    role: str
    name: str
    content: str


def convert_to_tool_call_message(chat_message: any) -> ToolCallMessage:
    tool_calls = [
        ToolCall(id=call.id, function=call.function, type=call.type)
        for call in chat_message.tool_calls
    ]
    return ToolCallMessage(
        content=chat_message.content, role=chat_message.role, tool_calls=tool_calls
    )


# Example usage
tool_call_message_data = {
    "content": None,
    "role": "assistant",
    "tool_calls": [
        {
            "id": "call_5yngVaYseZ0Y8z2kAm18u2QN",
            "function": {
                "arguments": '{"filename":"./fibo/fibo.py"}',
                "name": "read_file",
            },
            "type": "function",
        }
    ],
}

# tool_call_message = ToolCallMessage(**tool_call_message_data)
