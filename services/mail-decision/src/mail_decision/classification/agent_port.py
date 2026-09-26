from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class StructuredAgent(ABC):
    """Communication boundary used by classification, independent of LangChain."""

    @abstractmethod
    def ask(
        self,
        messages: list[tuple[str, str]],
        response_schema: type[BaseModel],
    ) -> dict[str, Any]:
        raise NotImplementedError
