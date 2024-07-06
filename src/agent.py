import schemas.anthropic as anthropic
from llm_client.llm_client import LLMClient
from memory.memory import DatabaseStorage, FileStorage, InMemoryStorage, MemoryInterface, StorageType
from schemas.agent import AgentConfig
from schemas.assistant import AssistantMessage
from schemas.chat_completion import ChatCompletion
from schemas.error import ErrorResponse
from schemas.message import Message
from schemas.message_param import MessageLike
from schemas.request_metadata import Metadata
from utils.logs import logger

_tag = "[Agent]"


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        memory: MemoryInterface,
    ):
        self.id = config.id
        self.config = config
        self.memory = memory
        self.llm_client = LLMClient(self.config)
        logger.info(f"{_tag} Create agent: {self.config.model_dump(exclude=['tools'])}")

    @classmethod
    async def create(
        cls,
        config: AgentConfig,
    ):
        memory_storage: MemoryInterface = cls.setup_memory_storage(
            storage_type=config.storage_type,
            config=config,
        )
        await memory_storage.init_messages()
        return cls(
            config=config,
            memory=memory_storage,
        )

    def setup_memory_storage(storage_type: StorageType, config: AgentConfig) -> MemoryInterface | None:
        memory = None
        if storage_type == StorageType.FILE:
            model_name = config.model.name
            if "/" in model_name:
                model_name = model_name.split("/")[1]
            name = f"{config.id}_{model_name.split('-')[0]}"
            memory = FileStorage(name=name, model=config.model)
        elif storage_type == StorageType.DATABASE:
            memory = DatabaseStorage()
        elif storage_type == StorageType.IN_MEMORY:
            memory = InMemoryStorage()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
        return memory

    async def send_prompt(self, content: str) -> MessageLike:
        await self.memory.save(Message(role="user", content=content))
        response = await self.llm_client.send_completion_request(
            memory=self.memory,
            metadata=Metadata(last_user_message=content),
        )
        try:
            if isinstance(response, ErrorResponse):
                return response
            elif isinstance(response, ChatCompletion):
                message = AssistantMessage(**response.choices[0].message.model_dump())
                return Message(role="assistant", content=message.content)
            elif isinstance(response, anthropic.Message):
                res = anthropic.AnthropicAssistantMessage(**response.model_dump())
                return Message(role="assistant", content=res.content[0].text)
            else:
                logger.error(f"Unexpected response: {response}")
                return response
        except Exception as e:
            return ErrorResponse(
                error=f"Error in parsing response: {response}",
                detail=f"Error in sending prompt: {e}",
            )

    async def send_request(self, memory: MemoryInterface):
        """Send a one-time completion request to the LLM model."""
        try:
            response = await self.llm_client.send_completion_request(
                memory=memory,
                metadata=Metadata(),
            )
            return response
        except Exception as e:
            return ErrorResponse(
                message=f"Exception: {e}",
            )
