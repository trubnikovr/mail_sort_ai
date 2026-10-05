from dataclasses import dataclass, field
from math import ceil
from datetime import UTC, datetime, timedelta
from typing import Literal


REVIEW_DESTINATION_ID = "needs-review"


@dataclass(frozen=True, slots=True)
class ClaimedEmailJob:
    """A classification job claimed by a worker for one email."""

    id: str
    account_id: str
    provider_message_id: str
    email_record_id: str
    attempt: int = 1


@dataclass(frozen=True, slots=True)
class EmailContent:
    sender: str
    subject: str
    body: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    status: Literal["completed", "review"]
    destination_id: str | None
    source: Literal["ai_subject", "ai_body", "ndr_rule", "subject_filter"]
    confidence: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class ProcessingDeferred:
    """A processing use case handled the job and requested a worker pause."""

    pause_seconds: int = 0


@dataclass(slots=True)
class ProcessingContext:
    job: ClaimedEmailJob
    email: EmailContent | None = None
    prepared_email: EmailContent | None = None
    destinations: dict[str, str] = field(default_factory=dict)
    outcome: ProcessingOutcome | None = None


class DailyRequestLimitReached(RuntimeError):
    """Raised before an API call when the configured daily quota is exhausted."""

    def retry_delay_seconds(self) -> int:
        now = datetime.now(UTC)
        next_day = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return ceil((next_day - now).total_seconds())
