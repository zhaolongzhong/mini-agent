import os
import json
import logging

import anthropic

from ..utils import count_token, debug_print_messages
from ..schemas import AgentConfig, ErrorResponse, CompletionRequest, CompletionResponse
from .system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AnthropicClient:
    """
    - https://docs.anthropic.com/en/docs/quickstart
    - https://docs.anthropic.com/en/docs/about-claude/models
    - https://docs.anthropic.com/en/docs/build-with-claude/tool-use
    """

    def __init__(
        self,
        config: AgentConfig,
    ):
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("API key is missing in both config and settings.")

        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.config = config
        self.model = config.model
        self.message_from_template = """[{agent_id}]:"""
        logger.debug(f"[AnthropicClient] initialized with model: {self.model} {self.config.id}")

    async def send_completion_request(self, request: CompletionRequest) -> CompletionResponse:
        response = None
        error = None

        try:
            # The Messages API accepts a top-level `system` parameter, not \"system\" as an input message role.
            system_message_content = request.system_prompt_suffix
            messages = [msg for msg in request.messages if msg["role"] != "system"]
            system_message = {
                "text": f"{SYSTEM_PROMPT}{' ' + system_message_content if system_message_content else ''}",
                "type": "text",
                "cache_control": {"type": "ephemeral"},
            }
            messages = self._process_messages(messages)
            system_message_tokens = count_token(str(system_message))
            tool_tokens = count_token(str(request.tool_json))
            message_tokens = count_token(str(messages))
            input_tokens = {
                "system_tokens": system_message_tokens,
                "tool_tokens": tool_tokens,
                "message_tokens": message_tokens,
            }

            if request.enable_prompt_caching:
                logger.debug("_inject_prompt_caching")
                self._inject_prompt_caching(messages)

            logger.debug(
                f"input_tokens: {json.dumps(input_tokens, indent=4)} \nsystem_message: \n{json.dumps(system_message, indent=4)}"
                f"\ntools_json: {json.dumps(request.tool_json, indent=4)}"
            )
            debug_print_messages(messages, tag=f"{self.config.id} send_completion_request clean messages")
            if request.tool_json:
                response = await self.client.with_options(max_retries=2).beta.prompt_caching.messages.create(
                    model=request.model,
                    system=[system_message],
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    tools=request.tool_json,
                    betas=["prompt-caching-2024-07-31"],
                )
            else:
                response = await self.client.with_options(max_retries=2).beta.prompt_caching.messages.create(
                    model=request.model,
                    system=[system_message],
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    betas=["prompt-caching-2024-07-31"],
                )
        except anthropic.APIConnectionError as e:
            error = ErrorResponse(message=f"The server could not be reached. {e.__cause__}")
        except anthropic.RateLimitError as e:
            error = ErrorResponse(
                message=f"A 429 status code was received; we should back off a bit. {e.response}",
                code=str(e.status_code),
            )
        except anthropic.APIStatusError as e:
            message = f"Another non-200-range status code was received. {e.status_code}, {e.response.text}"
            debug_print_messages(messages, tag=f"{self.config.id} send_completion_request")
            error = ErrorResponse(
                message=message,
                code=str(e.status_code),
            )
        if error:
            logger.error(error.model_dump())
        return CompletionResponse(author=request.author, response=response, model=self.model, error=error)

    def format_message(self, message):
        """
        Formats a single message based on whether it has a name.
        """
        new_message = {"role": message["role"]}
        if "name" in message and message["name"] and "system" not in message["role"]:
            message_from = self.message_from_template.format(agent_id=message["name"])
            new_message["content"] = f"{message_from} {message['content']}"

        else:
            new_message["content"] = message["content"]
        return new_message

    def _validate_final_message_role(self, messages):
        """
        Ensures the final message has the 'user' role if it is 'assistant'.
        Ensure the last message has 'user' role, otherwise, we will get error:
        Your API request included an `assistant` message in the final position, which would pre-fill the `assistant` response. When using tools, pre-filling the `assistant` response is not supported.
        """
        if messages and messages[-1]["role"] == "assistant":
            messages[-1]["role"] = "user"
        return messages

    def _process_messages(self, messages):
        """
        Processes all messages, formatting and validating the final message role.
        """
        processed_messages = [self.format_message(msg) for msg in messages]
        return self._validate_final_message_role(processed_messages)

    def _inject_prompt_caching(self, messages):
        breakpoints_remaining = 3

        # Loop through messages from newest to oldest
        for message in reversed(messages):  # Message 5 -> 4 -> 3 -> 2 -> 1
            if message["role"] == "user" and isinstance(content := message["content"], list):
                if breakpoints_remaining:
                    # First 3 iterations (newest messages)
                    breakpoints_remaining -= 1
                    content[-1]["cache_control"] = {"type": "ephemeral"}
                    # Message 5: Set cache point 1
                    # Message 4: Set cache point 2
                    # Message 3: Set cache point 3
                else:
                    # First message encountered after breakpoints = 0
                    content[-1].pop("cache_control", None)  # Remove existing cache_control
                    break  # Stop processing older messages
