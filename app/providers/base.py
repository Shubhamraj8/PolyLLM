from abc import ABC, abstractmethod

from app.models.request import ChatRequest
from app.models.response import ChatResponse


class BaseProvider(ABC):
    name: str
    models: list[str]

    @abstractmethod
    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Execute the chat completion against the provider's API."""
        pass

    def supports_model(self, model: str) -> bool:
        """Check if this provider supports the requested model natively."""
        return model in self.models

    @abstractmethod
    def get_timeout(self) -> float:
        """Return the base timeout for this provider in seconds."""
        pass
