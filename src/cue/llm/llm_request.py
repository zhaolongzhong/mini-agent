from abc import ABC, abstractmethod

from ..memory import MemoryInterface
from ..schemas import Metadata


class LLMRequest(ABC):
    @abstractmethod
    async def send_completion_request(
        self,
        memory: MemoryInterface,
        metadata: Metadata,
    ):
        pass
