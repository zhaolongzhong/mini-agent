import os
from typing import Any

from dotenv import load_dotenv
from llm_client.llm_model import ChatModel
from pydantic import PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

load_dotenv(dotenv_path=".env")

from utils.logs import setup_logging as _setup_logging  # noqa: E402

_setup_logging()


api_key = os.getenv("OPENAI_API_KEY", "")


class Settings(BaseSettings):
    api_key: str = api_key
    chat_model: ChatModel = ChatModel.GPT_4O.value

    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    DATABASE_URI: str | None = None

    @field_validator("DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: str | None, info: ValidationInfo) -> Any:
        assert info.data is not None
        values = info.data
        if isinstance(v, str):
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                host=values.get("POSTGRES_HOST"),
                path=values.get("POSTGRES_DB"),
                port=values.get("POSTGRES_PORT"),
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
            )
        )

    class ConfigDict:
        use_enum_values = True


settings = Settings()
