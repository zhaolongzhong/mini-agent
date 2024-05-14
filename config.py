import os
from dotenv import load_dotenv
from core.chat_model import ChatModel

load_dotenv(dotenv_path=".env")

from utils.logs import setup_logging as _setup_logging  # noqa: E402

_setup_logging()


api_key = os.getenv("OPENAI_API_KEY")


class Settings:
    api_key = api_key
    chat_model = ChatModel.GPT_4O.value


settings = Settings()
