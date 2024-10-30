import uuid
from datetime import datetime


def generate_id(prefix: str = "", length: int = 21) -> str:
    """Generate a random ID with optional prefix and specified length."""
    return f"{prefix}{uuid.uuid4().hex[:length]}"


def generate_run_id(include_timestamp: bool = True) -> str:
    """
    Generate a run ID with optional timestamp.

    Args:
        include_timestamp (bool): If True, prepend timestamp to ID. Default: True

    Returns:
        str: Run ID in format: [YYYYMMDDHHMMSS-]{6 random chars}
    """
    unique_part = generate_id(length=6)
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{timestamp}-{unique_part}"
    return unique_part
