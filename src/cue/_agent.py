import logging
from typing import Optional, Union

from .llm import LLMClient
from .memory.memory import MemoryInterface, setup_memory_storage
from .schemas import (
    AgentConfig,
    ChatCompletion,
    CompletionResponse,
    ErrorResponse,
    Message,
    Metadata,
    anthropic,
)
from .utils.id_generator import generate_session_id

logger = logging.getLogger(__name__)


class Agent:
    """
    Represents an agent that interacts with an LLM (Large Language Model) client,
    manages session-based memory storage, and handles message exchanges.
    """

    _tag = "[Agent]"

    def __init__(
        self,
        config: AgentConfig,
        memory: MemoryInterface,
        session_id: str,
    ) -> None:
        """
        Initializes the Agent instance.

        Args:
            config (AgentConfig): Configuration for the agent.
            memory (MemoryInterface): Memory storage interface.
            session_id (str): Unique session identifier.
        """
        self.id: str = config.id
        self.session_id: str = session_id
        self.config: AgentConfig = config
        self.memory: MemoryInterface = memory
        self.llm_client: LLMClient = LLMClient(self.config)
        self.metadata: Optional[Metadata] = None

        logger.info(f"{self._tag} Created agent: {self.config.model_dump(exclude=['tools'])}")

    @classmethod
    async def create(cls, config: AgentConfig) -> "Agent":
        """
        Asynchronously creates an Agent instance with initialized memory storage.

        Args:
            config (AgentConfig): Configuration for the agent.

        Returns:
            Agent: An instance of the Agent class.
        """
        session_id = generate_session_id()
        memory_storage: MemoryInterface = setup_memory_storage(
            storage_type=config.storage_type, config=config, session_id=session_id
        )
        await memory_storage.init_messages()
        return cls(
            config=config,
            memory=memory_storage,
            session_id=session_id,
        )

    async def send_message(self, content: str) -> CompletionResponse:
        """
        Sends a user message to the LLM client and processes the response.

        Args:
            content (str): The message content from the user.

        Returns:
            CompletionResponse: The response from the LLM client.
        """
        self.metadata = Metadata(last_user_message=content, session_id=self.session_id)
        user_message = Message(role="user", content=content)
        await self.memory.save(user_message)
        logger.info(f"{self._tag} Saved user message to memory: {content}")

        try:
            response = await self.llm_client.send_completion_request(
                memory=self.memory,
                metadata=self.metadata,
            )
            logger.debug(f"{self._tag} Received response: {response}")

            if isinstance(response, ErrorResponse):
                logger.error(f"{self._tag} LLM returned an error: {response.message}")
                return CompletionResponse(model=self.config.model.model_id, error=response)
            elif isinstance(response, ChatCompletion) or isinstance(response, anthropic.Message):
                return CompletionResponse(model=self.config.model.model_id, response=response)
            else:
                logger.error(f"{self._tag} Unexpected response type: {type(response)} with content: {response}")
                return CompletionResponse(
                    model=self.config.model.model_id,
                    error=ErrorResponse(
                        message=f"Unexpected response type: {type(response)}",
                        detail=f"Response content: {response}",
                    ),
                )
        except Exception as e:
            logger.exception(f"{self._tag} Exception during send_message: {e}")
            return CompletionResponse(
                model=self.config.model.model_id,
                error=ErrorResponse(
                    message="Error in processing the response.",
                    detail=str(e),
                ),
            )

    async def send_request(self, memory: Optional[MemoryInterface] = None) -> CompletionResponse:
        """
        Sends a one-time completion request to the LLM model.

        Args:
            memory (Optional[MemoryInterface]): Optional memory interface to use for the request.

        Returns:
            CompletionResponse: The response from the LLM client.
        """
        memory_to_use = memory or self.memory
        try:
            response = await self.llm_client.send_completion_request(
                memory=memory_to_use,
                metadata=Metadata(session_id=self.session_id),
            )
            logger.debug(f"{self._tag} Received one-time response: {response}")

            if isinstance(response, ErrorResponse):
                logger.error(f"{self._tag} LLM returned an error on one-time request: {response.message}")
                return CompletionResponse(model=self.config.model.model_id, error=response)
            elif isinstance(response, Union(ChatCompletion, anthropic.Message)):
                return CompletionResponse(model=self.config.model.model_id, response=response)
            else:
                logger.error(
                    f"{self._tag} Unexpected response type in send_request: {type(response)} with content: {response}"
                )
                return CompletionResponse(
                    model=self.config.model.model_id,
                    error=ErrorResponse(
                        message=f"Unexpected response type: {type(response)}",
                        detail=f"Response content: {response}",
                    ),
                )
        except Exception as e:
            logger.exception(f"{self._tag} Exception during send_request: {e}")
            return CompletionResponse(
                model=self.config.model.model_id,
                error=ErrorResponse(
                    message="Exception occurred while sending request.",
                    detail=str(e),
                ),
            )

    def get_metadata(self) -> Optional[Metadata]:
        """
        Retrieves the current metadata of the agent.

        Returns:
            Optional[Metadata]: The metadata if available, else None.
        """
        logger.debug(f"{self._tag} Retrieving metadata: {self.metadata}")
        return self.metadata
