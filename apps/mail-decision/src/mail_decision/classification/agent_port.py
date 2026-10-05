from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AiBillingUnavailable(RuntimeError):
    """Raised when an AI provider rejects a request due to a billing limit."""

    def __init__(self, provider: str, error_code: str) -> None:
        self.provider = provider
        self.error_code = error_code
        super().__init__(f"AI billing limit reached: provider={provider} code={error_code}")


class StructuredAgent(ABC):
    """Communication boundary used by classification, independent of LangChain."""

    @abstractmethod
    def ask(
        self,
        messages: list[tuple[str, str]],
        response_schema: type[BaseModel],
    ) -> dict[str, Any]:
        raise NotImplementedError
