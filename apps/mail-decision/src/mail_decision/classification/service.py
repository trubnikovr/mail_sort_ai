from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .agent_port import StructuredAgent
from .prompt_builder import ClassificationPromptBuilder


class ClassificationResponse(BaseModel):
    action: Literal["classified", "need_body", "review"] = Field(
        description=(
            "classified: choose a supplied destination; review: uncertain, unknown, "
            "or correspondence requiring human handling; "
            "need_body: subject-only classification needs the message body"
        )
    )
    category: str | None = Field(default=None)
    destination_id: str | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str = Field(description="One concise explanation without quoting email content")

    @model_validator(mode="after")
    def validate_classified_response(self) -> "ClassificationResponse":
        if self.action == "classified" and (
            not self.category or not self.destination_id or self.confidence is None
        ):
            raise ValueError("A classified response requires category, destination_id, and confidence")
        if self.action == "review" and self.destination_id is not None:
            raise ValueError(f"A {self.action} response must not specify a destination_id")
        return self


class ClassificationService:
    """Builds classification prompts and submits them to the structured AI agent."""

    def __init__(self, agent: StructuredAgent, prompts: ClassificationPromptBuilder) -> None:
        self._agent = agent
        self._prompts = prompts

    def classify_subject(
        self,
        sender: str,
        subject: str,
        destinations: dict[str, str],
    ) -> ClassificationResponse:
        response = self._agent.ask(
            messages=self._prompts.for_subject(sender, subject, destinations),
            response_schema=ClassificationResponse,
        )
        return ClassificationResponse.model_validate(response)

    def classify_body(
        self,
        sender: str,
        subject: str,
        body: str,
        destinations: dict[str, str],
    ) -> ClassificationResponse:
        # print(self._prompts.for_body_classification(sender, subject, body, destinations))
        # exit()
        response = self._agent.ask(
            messages=self._prompts.for_body_classification(sender, subject, body, destinations),
            response_schema=ClassificationResponse,
        )
        return ClassificationResponse.model_validate(response)
