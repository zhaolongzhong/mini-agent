from typing import List

from pydantic import BaseModel


class ConversationContext(BaseModel):
    participants: List[str]
