from typing import Optional

from pydantic import BaseModel


class MessageParam(BaseModel):
    content: str
    role: str
    name: Optional[str] = None
