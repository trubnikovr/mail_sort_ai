from dataclasses import dataclass
from typing import Literal

MailProvider = Literal["imap", "ews"]
MailRouteAction = Literal["move"]
JobStatus = Literal["pending", "processing", "completed", "review", "failed"]


@dataclass(frozen=True, slots=True)
class ClassifyEmailJob:
    account_id: str
    provider: MailProvider
    provider_message_id: str
    idempotency_key: str
    email_record_id: str
    type: Literal["classify_email"] = "classify_email"


@dataclass(frozen=True, slots=True)
class RouteEmailJob:
    """Provider-neutral command published by mail-decision for mail-router."""

    account_id: str
    provider: MailProvider
    provider_message_id: str
    email_record_id: str
    idempotency_key: str
    action: MailRouteAction
    destination_id: str
    classification_job_id: str
    type: Literal["route_email"] = "route_email"


@dataclass(frozen=True, slots=True)
class ClassificationDecision:
    category: str
    destination_id: str
    confidence: float
    reason: str
