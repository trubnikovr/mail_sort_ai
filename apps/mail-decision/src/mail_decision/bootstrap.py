from mail_sort_database.session import create_session_factory

from .classification.prompt_builder import ClassificationPromptBuilder
from .classification.service import ClassificationService
from .infrastructure.ai_agent import AiAgent
from .infrastructure.diagnostics import DatabaseDiagnosticStore
from .infrastructure.email_record_reader import EmailRecordReader
from .infrastructure.langgraph_workflow import LangGraphWorkflow
from .infrastructure.persistence import (
    DatabaseDecisionControl,
    DailyAiRequestQuota,
    DestinationRepository,
    JobStore,
)
from .infrastructure.settings import Settings
from .processing.email_classification_process import EmailClassificationProcess
from .processing.steps.ai_rules.classify_by_body import ClassifyByBody
from .processing.steps.email.get_email import GetEmail
from .processing.steps.rules.detect_ndr import DetectNdr
from .processing.steps.rules.detect_configured_filters import DetectConfiguredFilters
from .processing.steps.email.prepare_data import PrepareData
from .processing.steps.limits.load_destinations import LoadDestinations
from .processing.steps.limits.acquire_ai_request_permit import AcquireAiRequestPermit
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
    jobs = JobStore(sessions, settings.worker_id)
    agent = build_ai_agent(settings)
    classifier = ClassificationService(agent, ClassificationPromptBuilder())
    steps = [
        GetEmail(EmailRecordReader(sessions)),
        LoadDestinations(destinations),
        DetectConfiguredFilters(),
        DetectNdr(),
        PrepareData(settings.ai_max_body_characters),
        AcquireAiRequestPermit(
            quota=DailyAiRequestQuota(sessions, settings.ai_daily_request_limit),
            provider=settings.ai_provider,
        ),
        ClassifyByBody(
            classifier=classifier,
            confidence_threshold=settings.ai_confidence_threshold,
        ),
    ]
    process = EmailClassificationProcess(
        steps=steps,
        results=jobs,
        diagnostics=DatabaseDiagnosticStore(sessions),
        failure_handler=jobs,
        workflow=LangGraphWorkflow(steps),
    )
    return JobWorker(
        process=process,
        jobs=jobs,
        retry_delay_seconds=settings.retry_delay_seconds,
        stale_job_timeout_seconds=settings.stale_job_timeout_seconds,
        control=DatabaseDecisionControl(sessions),
    )
