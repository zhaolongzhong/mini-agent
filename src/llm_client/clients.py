import httpx
from openai import AsyncOpenAI


def create_openai_client(api_key: str):
    client = AsyncOpenAI(
        api_key=api_key,
        # https://github.com/openai/openai-python#retries
        # https://github.com/openai/openai-python#timeouts
        # requests that time out are retried twice by default.
        timeout=httpx.Timeout(60.0, read=60.0, write=10.0, connect=2.0),
    )
    return client
