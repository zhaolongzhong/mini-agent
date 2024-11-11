from typing import Optional


def truncate_safely(text: Optional[str] = None, length=100):
    """Safely truncate text, handling None values."""
    if text is None:
        return None
    return str(text)[:length]
