from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from mail_decision.classification.agent_port import StructuredAgent


class AiAgent(StructuredAgent):
    """Generic LangChain client for requesting structured LLM responses.

    It selects and creates the configured model, then communicates with it.
    Domain prompts and interpretations of responses belong to the caller.
    """

    def __init__(self, provider: str, model_name: str, api_key: str) -> None:
        self._chat_model = self._create_chat_model(provider, model_name, api_key)
        self._structured_models: dict[type[BaseModel], Runnable[Any, Any]] = {}

    @staticmethod
    def _create_chat_model(
        provider: str,
        model_name: str,
        api_key: str,
    ) -> BaseChatModel:
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=1.0,
                retries=2,
            )
        raise ValueError(f"Unsupported AI_PROVIDER: {provider}")

    def ask(
        self,
        messages: list[tuple[str, str]],
        response_schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Invoke the model with a structured response contract."""
        structured_model = self._structured_models.get(response_schema)
        if structured_model is None:
            structured_model = self._chat_model.with_structured_output(response_schema)
            self._structured_models[response_schema] = structured_model

        response = structured_model.invoke(
            [
                {"role": "user" if role == "human" else role, "content": content}
                for role, content in messages
            ]
        )
        return response.model_dump() if isinstance(response, BaseModel) else response
