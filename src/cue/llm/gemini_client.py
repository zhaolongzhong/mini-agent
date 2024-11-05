import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

import openai
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account

from ..tools import ToolManager
from ..memory import MemoryInterface
from ..schemas import AgentConfig, RunMetadata, ErrorResponse
from .base_client import BaseClient
from .llm_request import LLMRequest
from ..schemas.tool_call import AssistantMessage, convert_to_assistant_message

logger = logging.getLogger(__name__)

_tag = ""


def create_gemini_api_key() -> str:
    # https://cloud.google.com/vertex-ai/docs/start/cloud-environment
    service_account_key_file = os.getenv("GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_FILE")
    service_account_key_file = f"credentials/{service_account_key_file}"
    service_account_key_file = Path(__file__).parent.parent.parent.parent / service_account_key_file
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = service_account.Credentials.from_service_account_file(service_account_key_file, scopes=SCOPES)
    # Refresh the access token
    # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library#openai-python
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    logger.debug(f"create_gemini_api_key token: {creds.token[0:8]}...{creds.token[-4:]}")
    return creds.token


def create_client(api_key: str) -> openai.OpenAI:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    LOCATION = "us-west1"  # https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations
    # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-openai-library#supported_models
    client = openai.AsyncOpenAI(
        base_url=f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{LOCATION}/endpoints/openapi",
        api_key=api_key,
    )
    return client


class GeminiClient(LLMRequest, BaseClient):
    def __init__(
        self,
        config: AgentConfig,
    ):
        api_key = config.api_key or create_gemini_api_key()
        if not api_key:
            raise ValueError("API key is missing in both config and settings.")
        self.client = create_client(api_key)
        self.confi = config
        self.model = config.model
        self.tools = config.tools
        self.tool_manager = ToolManager()
        if len(self.tools) > 0:
            self.tool_json = self.tool_manager.get_tool_definitions(self.model, self.tools)
        else:
            self.tool_json = None

        logger.debug(
            f"[GeminiClient] initialized with model: {self.model}, tools: {[tool.name for tool in self.tools]} {self.config.id}"
        )

    async def _send_completion_request(
        self,
        messages: List[Dict],
    ):
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag}send_completion_request message ({idx + 1}/{length}): {message.model_dump()}")
        try:
            if self.tool_json and len(self.tool_json) > 0:
                response = await self.client.chat.completions.create(
                    model=f"google/{self.model}",
                    messages=[
                        msg.model_dump(exclude={"tool_calls"})
                        if hasattr(msg, "tool_calls") and not msg.tool_calls
                        else msg.model_dump()
                        for msg in messages
                    ],
                    max_tokens=2048,
                    temperature=0.8,
                    tool_choice="auto",
                    tools=self.tool_json,
                )
            else:
                response = await self.client.chat.completions.create(
                    model=f"google/{self.model}",
                    messages=[
                        msg.model_dump(exclude={"tool_calls"})
                        if hasattr(msg, "tool_calls") and not msg.tool_calls
                        else msg.model_dump()
                        for msg in messages
                    ],
                    max_tokens=2048,
                    temperature=0.8,
                )
            logger.debug(f"usage: {response.usage.model_dump()}")
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
            logger.error(f"{message}")
            return ErrorResponse(
                message=message,
                code=str(e.status_code),
            )
        except Exception as e:
            return ErrorResponse(
                message=f"Exception: {e}",
            )

    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: RunMetadata,
    ) -> Optional[dict]:
        if metadata is None:
            metadata = RunMetadata()
        else:
            logger.debug(f"Metadata: {metadata.model_dump_json()}")

        if metadata.current_turn >= metadata.max_turns:
            response = input(f"Maximum depth of {metadata.max_turns} reached. Continue?" " (y/n): ")
            if response.lower() in ["y", "yes"]:
                metadata.current_turn = 0
            else:
                return None

        schema_messages = memory.get_message_params()
        response = await self._send_completion_request(schema_messages)
        if isinstance(response, ErrorResponse):
            return response

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            message = AssistantMessage(**response.choices[0].message.model_dump())
            await memory.save(message)
            return response  # return original response
        tool_call_message = convert_to_assistant_message(response.choices[0].message)
        await memory.save(tool_call_message)
        tool_responses = await self.process_tools_with_timeout(tool_calls, timeout=5)
        await memory.saveList(tool_responses)

        metadata = RunMetadata(
            user_messages=metadata.user_messages,
            current_turn=metadata.current_turn + 1,
        )

        return await self.send_completion_request(memory=memory, metadata=metadata)
