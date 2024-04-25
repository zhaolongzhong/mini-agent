import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

api_key = os.getenv("OPENAI_API_KEY")


class Settings:
    api_key = api_key


settings = Settings()
