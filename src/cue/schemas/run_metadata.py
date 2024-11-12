from typing import List

from pydantic import BaseModel


class RunMetadata(BaseModel):
    last_user_message: str = ""
    user_messages: List[str] = []
    run_id: str = ""
    max_turns: int = 30  # maximum turns per run
    current_turn: int = 0
    enable_turn_debug: bool = False  # enable debug for each turn
    enable_services: bool = False
    token_stats: dict = {}
    metrics: dict = {}
