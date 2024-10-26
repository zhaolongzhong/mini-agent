import logging
from typing import Optional

import tiktoken


def count_token(content: str, model: Optional[str] = None) -> int:
    """Return the rough number of tokens in a string.
    Reference:
    - https://github.com/openai/tiktoken
    - https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    """
    try:
        if model:
            if "gpt-4o" in model:
                encoding = tiktoken.get_encoding("o200k_base")
            elif "gpt-4" in model or "text-embedding" in model:
                encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))
    except Exception as e:
        logging.error(f"Error getting encoding: {e}")
        return 0
