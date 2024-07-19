import openai
from llm_client.base_client import BaseClient
from llm_client.llm_request import LLMRequest
from memory.memory import MemoryInterface
from openai import AsyncOpenAI
from schemas.agent import AgentConfig
from schemas.assistant import AssistantMessage, convert_to_assistant_message
from schemas.chat_completion import ChatCompletion
from schemas.error import ErrorResponse
from schemas.message_param import ChatCompletionMessageParam
from schemas.request_metadata import Metadata
from utils.logs import logger

_tag = ""


class TogetherAIClient(BaseClient, LLMRequest):
    def __init__(
        self,
        api_key,
        config: AgentConfig,
    ):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.together.xyz/v1",
        )

        self.model = config.model
        logger.info(
            f"[TogetherAIClient] initialized with model: {self.model}, tools: {[tool.name for tool in self.tools]}"
        )

    async def _send_completion_request(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> ChatCompletion:
        length = len(messages)
        for idx, message in enumerate(messages):
            logger.debug(f"{_tag}send_completion_request message ({idx + 1}/{length}): {message.model_dump()}")

        try:
            if self.tool_json and len(self.tool_json) > 0:
                chat_completion = await self.client.chat.completions.create(
                    messages=[msg.model_dump(exclude="name") for msg in messages],
                    model=self.model.model_id,
                    tools=self.tool_json,
                    tool_choice="auto",
                    max_tokens=2048,
                    temperature=0.8,
                )
            else:
                chat_completion = await self.client.chat.completions.create(
                    messages=[msg.model_dump() for msg in messages],
                    model=self.model.model_id,
                )
            # chat_completion = await self.client.chat.completions.create(
            #     messages=[msg.model_dump() for msg in messages],
            #     model=self.model,
            # )

            chat_completion = ChatCompletion(**chat_completion.model_dump())
            logger.info(f"send_completion_request usage: {chat_completion.usage.model_dump()}")
            return chat_completion
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
        metadata: Metadata,
    ) -> dict | None:
        if metadata is None:
            metadata = Metadata()
        else:
            logger.debug(f"Metadata: {metadata.model_dump_json()}")

        if metadata.current_depth >= metadata.max_depth:
            response = input(f"Maximum depth of {metadata.max_depth} reached. Continue?" " (y/n): ")
            if response.lower() in ["y", "yes"]:
                metadata.current_depth = 0
            else:
                return None

        schema_messages = memory.get_message_params()
        response = await self._send_completion_request(schema_messages)
        if isinstance(response, ErrorResponse):
            return response
        metadata.current_depth += 1
        metadata.total_depth += 1
        metadata.request_count += 1
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls is None:
            message = AssistantMessage(**response.choices[0].message.model_dump())
            await memory.save(message)
            return response  # return original response
        tool_call_message = convert_to_assistant_message(response.choices[0].message)
        await memory.save(tool_call_message)
        tool_responses = await self.process_tools_with_timeout(tool_calls, timeout=5)
        await memory.saveList(tool_responses)

        metadata = Metadata(
            last_user_message=metadata.last_user_message,
            current_depth=metadata.current_depth + 1,
            total_depth=metadata.total_depth + 1,
        )

        return await self.send_completion_request(memory=memory, metadata=metadata)
