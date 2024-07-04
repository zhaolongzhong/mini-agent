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
        tools_manager,
    ):
        self.config = config
        self.memory = memory
        self.tools_manager = tools_manager
        self.llm_client = LLMClient(self.config.model, self.tools_manager)
        logger.debug(f"{_tag} AgentConfig: {self.config.model_dump()}")

    @classmethod
    async def create(
        cls,
        config: AgentConfig,
        tools_manager,
    ):
        memory_storage: MemoryInterface = cls.setup_memory_storage(
            storage_type=config.storage_type,
            model=config.model,
        )
        await memory_storage.init_messages()
        return cls(
            config=config,
            memory=memory_storage,
            tools_manager=tools_manager,
        )

    def setup_memory_storage(storage_type: StorageType, model: str) -> MemoryInterface | None:
        memory = None
        if storage_type == StorageType.FILE:
            memory = FileStorage(name=model.split("-")[0])
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
