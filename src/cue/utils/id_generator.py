import uuid
from datetime import datetime


def generate_id(prefix: str = "", length: int = 21) -> str:
    return f"{prefix}{uuid.uuid4().hex[:length]}"


def generate_session_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Format: YYYYMMDDHHMMSS
    unique_part = generate_id(6)
    return f"{timestamp}-{unique_part}"
