"""Run the Mail Decision classifier against an email snapshot without persisting."""

import argparse
from pathlib import Path
import os
from uuid import UUID

from sqlalchemy import select

from mail_sort_database.models import EmailRecord, Job
from mail_sort_database.session import create_session_factory, session_scope
from mail_decision.bootstrap import build_ai_agent
from mail_decision.classification.prompt_builder import ClassificationPromptBuilder
from mail_decision.classification.service import ClassificationService
from mail_decision.infrastructure.persistence import DestinationRepository
from mail_decision.infrastructure.settings import Settings
from mail_decision.processing.context import ClaimedEmailJob, EmailContent, ProcessingContext
from mail_decision.processing.steps.ai_rules.classify_by_body import ClassifyByBody
from mail_decision.processing.steps.email.get_email import GetEmail
from mail_decision.processing.steps.email.prepare_data import PrepareData
from mail_decision.processing.steps.rules.detect_configured_filters import DetectConfiguredFilters
from mail_decision.processing.steps.rules.detect_ndr import DetectNdr
from mail_decision.processing.steps.limits.validate_ai_request import ValidateAiRequest


class _MemoryEmailReader:
    def __init__(self, email: EmailRecord) -> None:
        self._email = email

    def read(self, job: ClaimedEmailJob) -> EmailContent:
        return EmailContent(
            sender=self._email.headers.get("from", ""),
            subject=self._email.subject,
            body=self._email.body,
            headers=self._email.headers,
        )


def _load_env() -> None:
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        raise SystemExit("Не найден .env в корне проекта")
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _find_email(identifier: str, settings: Settings) -> tuple[EmailRecord, str]:
    sessions = create_session_factory(settings.database_url)
    with session_scope(sessions) as session:
        try:
            job_id = UUID(identifier)
        except ValueError:
            job_id = None

        if job_id is not None:
            job = session.get(Job, job_id)
            if job is not None:
                if job.account_id != settings.mailbox_account_id:
                    raise LookupError("Job belongs to a different MAILBOX_ACCOUNT_ID")
                record = session.get(EmailRecord, job.email_record_id) if job.email_record_id else None
                if record is not None:
                    return record, str(job.id)
            record = session.get(EmailRecord, job_id)
            if record is not None and record.account_id == settings.mailbox_account_id:
                return record, "no job"

        record = session.scalar(
            select(EmailRecord).where(
                EmailRecord.account_id == settings.mailbox_account_id,
                EmailRecord.provider_message_id == identifier,
            )
        )
        if record is not None:
            return record, "no job"
    raise LookupError(f"Email or job not found for ID: {identifier}")


def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser(
        description="Classify a stored email using Mail Decision without changing jobs"
    )
    parser.add_argument("email_id", help="Job UUID, email record UUID, or provider message ID")
    arguments = parser.parse_args()
    settings = Settings.from_environment()
    email, job_id = _find_email(arguments.email_id, settings)

    job = ClaimedEmailJob(
        id=job_id,
        account_id=email.account_id,
        provider_message_id=email.provider_message_id,
        email_record_id=str(email.id),
    )
    destinations = DestinationRepository(settings.mailbox_account_id)
    classifier = ClassificationService(build_ai_agent(settings), ClassificationPromptBuilder())
    context = ProcessingContext(job=job)
    steps = (
        GetEmail(_MemoryEmailReader(email)),
        DetectConfiguredFilters(),
        DetectNdr(destinations),
        PrepareData(settings.ai_max_body_characters),
        ValidateAiRequest(destinations),
        ClassifyByBody(classifier, settings.ai_confidence_threshold),
    )
    for step in steps:
        step.execute(context)
        if context.outcome is not None:
            break

    result = context.outcome
    if result is None:
        raise RuntimeError("Classifier finished without a decision")
    print(f"Email ID: {email.provider_message_id}")
    print(f"Subject: {email.subject}")
    print(f"Status: {result.status}")
    print(f"Destination: {result.destination_id or '(none; email stays in Inbox)'}")
    print(f"Source: {result.source}")
    print(f"Confidence: {result.confidence if result.confidence is not None else '(n/a)'}")
    print(f"Reason: {result.reason}")
    print("Note: diagnostic only; no job or route was saved.")


if __name__ == "__main__":
    main()
