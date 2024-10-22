import logging
import os

import openai
from pydantic import BaseModel

from ..schemas import AgentConfig, CompletionRequest, CompletionResponse, ErrorResponse
from ..schemas.chat_completion import ChatCompletion
from ..utils.debug_utils import debug_print_messages
from .llm_request import LLMRequest

logger = logging.getLogger(__name__)


class OpenAIClient(LLMRequest):
    def __init__(
        self,
        config: AgentConfig,
    ):
        api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("API key is missing in both config and settings.")

        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.config = config
        self.model = config.model
        logger.info(f"[OpenAIClient] initialized with model: {self.model} {self.config.id}")

    async def send_completion_request(self, request: CompletionRequest) -> CompletionResponse:
        self.tool_json = request.tool_json
        response = None
        error = None
        try:
            messages = [
                msg.model_dump(exclude_none=True, exclude_unset=True) if isinstance(msg, BaseModel) else msg
                for msg in request.messages
            ]
            debug_print_messages(messages, tag=f"{self.config.id} send_completion_request")
            if self.tool_json:
                response = await self.client.chat.completions.create(
                    messages=messages,
                    model=self.model.model_id,
                    max_completion_tokens=request.max_tokens,
                    temperature=request.temperature,
                    response_format=request.response_format,
                    tool_choice=request.tool_choice,
                    tools=self.tool_json,
                )
            else:
                response = await self.client.chat.completions.create(
                    messages=messages,
                    model=self.model.model_id,
                    max_completion_tokens=request.max_tokens,
                    temperature=request.temperature,
                    response_format=request.response_format,
                )

            response = ChatCompletion(**response.model_dump())
        except openai.APIConnectionError as e:
            error = ErrorResponse(message=f"The server could not be reached. {e.__cause__}")
        except openai.RateLimitError as e:
            error = ErrorResponse(
                message=f"A 429 status code was received; we should back off a bit. {e.response}",
                code=str(e.status_code),
            )
        except openai.APIStatusError as e:
            message = f"Another non-200-range status code was received. {e.response}, {e.response.text}"
            debug_print_messages(messages, tag=f"{self.config.id} send_completion_request")
            error = ErrorResponse(
                message=message,
                code=str(e.status_code),
            )
        except Exception as e:
            error = ErrorResponse(
                message=f"Exception: {e}",
            )
        if error:
            logger.error(error.model_dump())
        return CompletionResponse(self.model, response, error=error)
