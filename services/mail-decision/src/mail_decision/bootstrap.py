from mail_sort_database.session import create_session_factory

from .classification.prompt_builder import ClassificationPromptBuilder
from .classification.service import ClassificationService
from .infrastructure.ai_agent import AiAgent
from .infrastructure.email_record_reader import EmailRecordReader
from .infrastructure.persistence import (
    DailyAiRequestQuota,
    DestinationRepository,
    JobStore,
)
from .infrastructure.settings import Settings
from .processing.email_classification_process import EmailClassificationProcess
from .processing.context import REVIEW_DESTINATION_ID
from .processing.steps.classify_by_body import ClassifyByBody
from .processing.steps.classify_by_subject import ClassifyBySubject
from .processing.steps.get_email import GetEmail
from .processing.steps.mark_as_done import MarkAsDone
from .processing.steps.prepare_data import PrepareData
from .processing.steps.validate_ai_request import ValidateAiRequest
from .processing.worker import JobWorker


def build_ai_agent(settings: Settings) -> AiAgent:
    return AiAgent(
        provider=settings.ai_provider,
        model_name=settings.ai_model,
        api_key=settings.ai_api_key,
    )


def build_worker(settings: Settings) -> JobWorker:
    sessions = create_session_factory(settings.database_url)
    destinations = DestinationRepository(sessions)
    active_destinations = destinations.active_for_account(settings.mailbox_account_id)
    if not active_destinations:
        raise ValueError(
            "No active destinations configured for MAILBOX_ACCOUNT_ID="
            f"{settings.mailbox_account_id!r}; add at least one row to destinations"
        )
    if REVIEW_DESTINATION_ID not in active_destinations:
        raise ValueError(
            f"Active review destination {REVIEW_DESTINATION_ID!r} is missing for "
            f"MAILBOX_ACCOUNT_ID={settings.mailbox_account_id!r}"
        )
    jobs = JobStore(sessions, settings.worker_id)
    agent = build_ai_agent(settings)
    classifier = ClassificationService(agent, ClassificationPromptBuilder())
    validate_ai_request = ValidateAiRequest(
        destinations=destinations,
        quota=DailyAiRequestQuota(sessions, settings.ai_max_requests_per_day),
        provider=settings.ai_provider,
    )
    process = EmailClassificationProcess(
        steps=[
            GetEmail(EmailRecordReader(sessions)),
            PrepareData(settings.ai_max_body_characters),
            validate_ai_request,
            ClassifyBySubject(
                classifier=classifier,
                confidence_threshold=settings.subject_confidence_threshold,
            ),
            # Reserve another request only if subject classification needs the body.
            validate_ai_request,
            ClassifyByBody(
                classifier=classifier,
                confidence_threshold=settings.ai_confidence_threshold,
            ),
            MarkAsDone(jobs),
        ]
    )
    return JobWorker(
        process=process,
        jobs=jobs,
        retry_delay_seconds=settings.retry_delay_seconds,
        stale_job_timeout_seconds=settings.stale_job_timeout_seconds,
    )
