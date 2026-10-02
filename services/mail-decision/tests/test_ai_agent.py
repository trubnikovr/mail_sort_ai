import unittest
from unittest.mock import Mock, patch

from pydantic import BaseModel

from mail_decision.infrastructure.ai_agent import AiAgent


class Answer(BaseModel):
    destination: str


class AiAgentTest(unittest.TestCase):
    def test_initializes_both_providers_with_explicit_key(self) -> None:
        for provider, model in (("openai", "gpt-test-model"), ("gemini", "gemini-test-model")):
            with self.subTest(provider=provider):
                agent = AiAgent(provider, model, "test-key")
                self.assertEqual(
                    getattr(agent._chat_model, "model_name" if provider == "openai" else "model"), model
                )
                agent._chat_model.with_structured_output(Answer, include_raw=True)

    def test_structured_response_and_schema_cache(self) -> None:
        with patch("mail_decision.infrastructure.ai_agent.init_chat_model") as factory:
            model = factory.return_value
            structured = Mock()
            model.with_structured_output.return_value = structured
            structured.invoke.return_value = {"parsed": Answer(destination="sales"), "raw": None, "parsing_error": None}
            agent = AiAgent("openai", "gpt-test-model", "test-key")
            for _ in range(2):
                self.assertEqual(agent.ask([("human", "Classify")], Answer), {"destination": "sales"})
            model.with_structured_output.assert_called_once_with(Answer, include_raw=True)
            structured.invoke.assert_called_with([{"role": "user", "content": "Classify"}])
            factory.assert_called_once_with(model="gpt-test-model", model_provider="openai", api_key="test-key")

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported AI_PROVIDER"):
            AiAgent("unknown", "test-model", "test-key")
