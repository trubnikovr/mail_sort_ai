import logging
from time import perf_counter
from uuid import uuid4

from mail_sort_logging import add_log_context, log_context

from mail_decision.classification.agent_port import AiBillingUnavailable

from .context import (
    ClaimedEmailJob,
    DailyRequestLimitReached,
    ProcessingContext,
    ProcessingDeferred,
    ProcessingOutcome,
)
from .statistics.diagnostics import DiagnosticScope, DiagnosticStore, current_diagnostics
from .steps.interface import ProcessingStep
from .ports import ClassificationResultStore, ProcessingFailureHandler

logger = logging.getLogger(__name__)


class EmailClassificationProcess:
    """Runs steps until a decision, then persists it exactly once per execution."""

    def __init__(self, steps: list[ProcessingStep], results: ClassificationResultStore,
                 diagnostics: DiagnosticStore | None = None,
                 failure_handler: ProcessingFailureHandler | None = None) -> None:
        self._steps = steps
        self._results = results
        self._diagnostics = diagnostics
        self._failure_handler = failure_handler

    def execute(self, job: ClaimedEmailJob) -> ProcessingOutcome | ProcessingDeferred:
        scope = (DiagnosticScope(self._diagnostics, job.id, str(uuid4()), job.attempt)
                 if self._diagnostics else None)
        token = current_diagnostics.set(scope)
        try:
            with log_context(
                job_id=job.id,
                account_id=job.account_id,
                provider_message_id=job.provider_message_id,
                attempt=job.attempt,
                run_id=scope.run_id if scope else None,
            ):
                try:
                    return self._execute(job, scope)
                except AiBillingUnavailable as error:
                    if self._failure_handler is None:
                        raise
                    try:
                        self._failure_handler.pause_for_billing_failure(
                            job.id, error.provider, error.error_code
                        )
                    except Exception:
                        logger.exception(
                            "billing failure handling was incomplete: job_id=%s provider=%s code=%s",
                            job.id, error.provider, error.error_code,
                        )
                        raise
                    logger.critical(
                        "decision paused after AI billing failure; alert queued: job_id=%s provider=%s code=%s",
                        job.id, error.provider, error.error_code,
                    )
                    return ProcessingDeferred()
                except DailyRequestLimitReached as error:
                    if self._failure_handler is None:
                        raise
                    delay = error.retry_delay_seconds()
                    try:
                        self._failure_handler.defer(job.id, error, delay)
                    except Exception:
                        logger.exception(
                            "failed to defer job after daily AI quota exhaustion: job_id=%s",
                            job.id,
                        )
                        raise
                    logger.info("daily AI quota exhausted: processing paused for %s seconds", delay)
                    return ProcessingDeferred(pause_seconds=delay)
        finally:
            current_diagnostics.reset(token)

    def _execute(self, job: ClaimedEmailJob, scope: DiagnosticScope | None) -> ProcessingOutcome:
        context = ProcessingContext(job=job)
        decision_step = None
        last_step = None

        def record(status: str, **details) -> None:
            if scope:
                scope.record("step", status=status, details=details)

        for number, step in enumerate(self._steps, start=1):
            last_step = type(step).__name__
            if scope:
                scope.step, scope.step_number = last_step, number
                scope.destinations = set(context.destinations)
            started = perf_counter()
            record("started")
            logger.info("step started: job_id=%s step=%s name=%s", job.id, number, last_step)
            try:
                step.execute(context)
                if context.email is not None:
                    add_log_context(subject=context.email.subject)
            except Exception as error:
                record("deferred" if isinstance(error, DailyRequestLimitReached) else "failed",
                       error_type=type(error).__name__, duration_seconds=perf_counter() - started,
                       last_step=last_step, decision_step=None, finalization="not_started")
                raise
            if context.outcome is not None:
                decision_step = last_step
            record("decision_made" if decision_step else "completed",
                   duration_seconds=perf_counter() - started,
                   decision_step=decision_step, last_step=last_step,
                   destination_id=context.outcome.destination_id if context.outcome else None,
                   outcome_status=context.outcome.status if context.outcome else None)
            if context.outcome is not None:
                break

        if scope:
            scope.step, scope.step_number = "finalize", len(self._steps) + 1
        if context.outcome is None:
            record("failed", error_type="MissingOutcome", last_step=last_step,
                   decision_step=None, finalization="not_started")
            raise RuntimeError("Classification steps completed without an outcome")
        started = perf_counter()
        record("started", decision_step=decision_step, last_step=last_step)
        try:
            self._results.finalize(job, context.outcome)
        except Exception as error:
            record("failed", error_type=type(error).__name__, decision_step=decision_step,
                   last_step=last_step, finalization="failed", duration_seconds=perf_counter() - started)
            raise
        record("completed", decision_step=decision_step, last_step=last_step,
               finalization="completed", duration_seconds=perf_counter() - started)
        logger.info("classification finalized: job_id=%s decision_step=%s", job.id, decision_step)
        return context.outcome
