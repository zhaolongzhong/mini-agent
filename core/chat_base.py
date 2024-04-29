from core.client import create_openai_client
from config import settings


class ChatBase:
    def __init__(self, mode: str = "gpt-4-turbo", tools: list = []):
        self.mode = mode
        self.client = create_openai_client(settings.api_key)
        self.tools = tools

    def send_request(self, messages: list = [], use_tools=False):
        if not use_tools:
            response = self.client.chat.completions.create(
                model=self.mode, messages=messages
            )
            return response

        if len(self.tools) == 0:
            raise Exception("No tools provided")

        response = self.client.chat.completions.create(
            model=self.mode,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
        )
        return response
