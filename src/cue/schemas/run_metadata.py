from typing import List

from pydantic import BaseModel


class RunMetadata(BaseModel):
    last_user_message: str = ""
    user_messages: List[str] = []
    session_id: str = ""
    max_turns: int = 4  # maximum turns per run
    current_depth: int = 0  # current_path can be reset if it reaches to max_depth
    total_depth: int = 0  # total_path since last user message
