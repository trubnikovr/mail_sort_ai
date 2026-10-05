from typing import Any
from time import perf_counter
from uuid import uuid4
import json

from mail_decision.processing.statistics.diagnostics import current_diagnostics

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from mail_decision.classification.agent_port import AiBillingUnavailable, StructuredAgent


class AiAgent(StructuredAgent):
    """Generic LangChain client for requesting structured LLM responses.

    It selects and creates the configured model, then communicates with it.
    Domain prompts and interpretations of responses belong to the caller.
    """

    def __init__(self, provider: str, model_name: str, api_key: str) -> None:
        self._provider = provider
        self._model_name = model_name
        self._chat_model = self._create_chat_model(provider, model_name, api_key)
        self._structured_models: dict[type[BaseModel], Runnable[Any, Any]] = {}

    @staticmethod
    def _create_chat_model(
        provider: str,
        model_name: str,
        api_key: str,
    ) -> BaseChatModel:
        providers = {"gemini": "google_genai", "openai": "openai"}
        if provider not in providers:
            raise ValueError(f"Unsupported AI_PROVIDER: {provider}")
        return init_chat_model(
            model=model_name,
            model_provider=providers[provider],
            api_key=api_key,
        )

    def ask(
        self,
        messages: list[tuple[str, str]],
        response_schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Invoke the model with a structured response contract."""
        scope = current_diagnostics.get()
        request_id, started = str(uuid4()), perf_counter()

        def record(status: str, **details: Any) -> None:
            if scope:
                scope.record("ai", status=status, details=dict(
                    request_id=request_id, provider=self._provider, model=self._model_name,
                    prompt_version="classification-v2", duration_seconds=perf_counter() - started,
                    **details,
                ))

        record("started")
        try:
            structured_model = self._structured_models.get(response_schema)
            if structured_model is None:
                structured_model = self._chat_model.with_structured_output(response_schema, include_raw=True)
                self._structured_models[response_schema] = structured_model
            response = structured_model.invoke([
                {"role": "user" if role == "human" else role, "content": content}
                for role, content in messages
            ])
            parsed = response.get("parsed")
            raw = response.get("raw")
            error = response.get("parsing_error")
            value = parsed.model_dump() if isinstance(parsed, BaseModel) else parsed
            # On schema errors recover only structured JSON, never persist raw text.
            if value is None and raw is not None:
                calls = getattr(raw, "tool_calls", [])
                if isinstance(calls, list) and calls:
                    value = calls[0].get("args")
                if value is None and isinstance(getattr(raw, "content", None), str):
                    try:
                        value = json.loads(raw.content)
                    except (ValueError, TypeError):
                        pass
            safe = self._safe_response(value, scope.destinations if scope else set())
            usage = getattr(raw, "usage_metadata", None)
            tokens = {key: usage[key] for key in ("input_tokens", "output_tokens", "total_tokens")
                      if isinstance(usage, dict) and type(usage.get(key)) is int}
            record("response_received", response=safe, tokens=tokens,
                   validation="invalid" if error or parsed is None else "valid",
                   error_type=type(error).__name__ if error else None)
            if error:
                raise error
            if parsed is None:
                raise ValueError("Model returned no structured response")
            return parsed.model_dump() if isinstance(parsed, BaseModel) else parsed
        except Exception as error:
            error_code = self._billing_error_code(error)
            record("failed", error_type=type(error).__name__, provider_error_code=error_code)
            if error_code is not None:
                raise AiBillingUnavailable(self._provider, error_code) from error
            raise

    def _billing_error_code(self, error: Exception) -> str | None:
        errors = self._exception_chain(error)
        if self._provider == "openai":
            billing_codes = {
                "insufficient_quota",
                "credit_balance_exhausted",
                "organization_usage_limit_exceeded",
                "organization_spend_limit_exceeded",
                "project_spend_limit_exceeded",
            }
            for provider_error in errors:
                body = getattr(provider_error, "body", None)
                payloads = [body]
                if isinstance(body, dict) and isinstance(body.get("error"), dict):
                    payloads.append(body["error"])
                payloads.append({
                    "code": getattr(provider_error, "code", None),
                    "type": getattr(provider_error, "type", None),
                })
                for payload in payloads:
                    if not isinstance(payload, dict):
                        continue
                    for field in ("code", "type"):
                        value = payload.get(field)
                        normalized = str(value).strip().lower() if value is not None else ""
                        if normalized in billing_codes:
                            return normalized

        if self._provider == "gemini":
            billing_markers = {
                "billing_disabled",
                "billing_not_enabled",
                "credit_balance_exhausted",
                "insufficient_credits",
                "payment_required",
                "prepay_credits_exhausted",
                "spend_limit_exceeded",
            }
            for provider_error in errors:
                details = getattr(provider_error, "details", None)
                markers = self._structured_error_markers(details)
                status = str(getattr(provider_error, "status", "")).strip().lower()
                http_code = getattr(provider_error, "code", None)
                if http_code == 402 or status == "payment_required":
                    return "payment_required"
                if status == "failed_precondition" and markers & billing_markers:
                    return sorted(markers & billing_markers)[0]
                if status == "resource_exhausted":
                    resource_billing_markers = {
                        marker for marker in markers
                        if any(token in marker for token in ("spend", "billing", "credit", "prepay", "payment"))
                    }
                    if resource_billing_markers:
                        return sorted(resource_billing_markers)[0]
        return None

    @staticmethod
    def _exception_chain(error: Exception) -> list[Exception]:
        chain: list[Exception] = []
        pending: list[Exception] = [error]
        seen: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            chain.append(current)
            for nested in (current.__cause__, current.__context__):
                if isinstance(nested, Exception):
                    pending.append(nested)
        return chain

    @classmethod
    def _structured_error_markers(cls, value: Any) -> set[str]:
        markers: set[str] = set()
        relevant_fields = {"code", "type", "status", "reason", "quotaid", "quotametric"}
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).replace("_", "").lower() in relevant_fields:
                    if isinstance(child, str):
                        markers.add(child.strip().lower().replace("-", "_").replace(" ", "_"))
                markers.update(cls._structured_error_markers(child))
        elif isinstance(value, (list, tuple)):
            for child in value:
                markers.update(cls._structured_error_markers(child))
        return markers

    @staticmethod
    def _safe_response(value: Any, destinations: set[str]) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {"redacted": True}
        safe: dict[str, Any] = {"redacted": True}
        if value.get("action") in ("classified", "need_body", "move", "review"):
            safe["action"] = value["action"]
        confidence = value.get("confidence")
        if type(confidence) in (int, float) and 0 <= confidence <= 1:
            safe["confidence"] = confidence
        destination = value.get("destination_id")
        if isinstance(destination, str) and destination in destinations:
            safe["destination_id"] = destination
        elif destination is not None:
            safe["destination_invalid"] = True
        # Free-text category/reason and unknown fields may repeat mail bodies or secrets.
        return safe
