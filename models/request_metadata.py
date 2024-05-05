from pydantic import BaseModel


class Metadata(BaseModel):
    last_user_message: str = ""
    current_depth: int = 0  # current_path can be reset if it reaches to max_depth
    total_depth: int = 0  # total_path since last user message
    max_depth: int = 8  # max_path to reach before resetting current_path
