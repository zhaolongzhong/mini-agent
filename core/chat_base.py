import openai
from core.client import create_openai_client
from config import settings
from models.error import ErrorResponse


class ChatBase:
    def __init__(self, mode: str = "gpt-4-turbo", tools: list = []):
        self.mode = mode
        self.client = create_openai_client(settings.api_key)
        self.tools = tools

    async def send_request(self, messages: list = [], use_tools=False):
        try:
            if not use_tools:
                response = await self.client.chat.completions.create(
                    model=self.mode, messages=messages
                )
                return response

            if len(self.tools) == 0:
                return ErrorResponse(
                    message="No tools provided",
                )
            response = await self.client.chat.completions.create(
                model=self.mode,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            return response
        except openai.APIConnectionError as e:
            return ErrorResponse(
                message=f"The server could not be reached. {e.__cause__}"
            )
        except openai.RateLimitError as e:
            return ErrorResponse(
                message=f"A 429 status code was received; we should back off a bit. {e.response}",
                code=str(e.status_code),
            )
        except openai.APIStatusError as e:
            return ErrorResponse(
                message=f"Another non-200-range status code was received. {e.response}",
                code=str(e.status_code),
            )
        except Exception as e:
            return ErrorResponse(
                message=f"Exception: {e}",
            )
