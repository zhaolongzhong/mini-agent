from abc import ABC, abstractmethod

from memory.memory import MemoryInterface
from schemas.request_metadata import Metadata


class LLMRequest(ABC):
    @abstractmethod
    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ):
        pass
