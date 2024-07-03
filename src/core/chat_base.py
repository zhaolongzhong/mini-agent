import logging

import openai
from config import settings
from llm_client import LLMClient
from models.error import ErrorResponse

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ChatBase:
    def __init__(self, model: str = settings.chat_model, tools: list = []):
        self.model = model
        self.client_wrapper = LLMClient(settings.api_key)
        self.tools = tools

    async def send_request(self, messages: list = [], use_tools=False):
        try:
            message_params = []
            for msg in messages:
                exclude_fields = {"name"} if not hasattr(msg, "name") or msg.name is None else set()
                message_params.append(msg.model_dump(exclude_none=True, exclude=exclude_fields))
            if not use_tools:
                response = await self.client_wrapper.send_request(model=self.model, messages=message_params)
                return response

            if len(self.tools) == 0:
                return ErrorResponse(
                    message="No tools provided",
                )
            response = await self.client_wrapper.send_request(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            return response
        except openai.APIConnectionError as e:
            return ErrorResponse(message=f"The server could not be reached. {e.__cause__}")
        except openai.RateLimitError as e:
            return ErrorResponse(
                message=f"A 429 status code was received; we should back off a bit. {e.response}",
                code=str(e.status_code),
            )
        except openai.APIStatusError as e:
            message = f"Another non-200-range status code was received. {e.response}, {e.response.text}"
            return ErrorResponse(
                message=message,
                code=str(e.status_code),
            )
        except Exception as e:
            return ErrorResponse(
                message=f"Exception: {e}",
            )
