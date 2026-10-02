import logging
from time import perf_counter
from uuid import uuid4

from .context import ClaimedEmailJob, ProcessingContext, ProcessingOutcome, DailyRequestLimitReached
from .statistics.diagnostics import DiagnosticScope, DiagnosticStore, current_diagnostics
from .steps.interface import ProcessingStep
from .ports import ClassificationResultStore

logger = logging.getLogger(__name__)


class EmailClassificationProcess:
    """Runs steps until a decision, then persists it exactly once per execution."""

    def __init__(self, steps: list[ProcessingStep], results: ClassificationResultStore,
                 diagnostics: DiagnosticStore | None = None) -> None:
        self._steps = steps
        self._results = results
        self._diagnostics = diagnostics

    def execute(self, job: ClaimedEmailJob) -> ProcessingOutcome:
        scope = (DiagnosticScope(self._diagnostics, job.id, str(uuid4()), job.attempt)
                 if self._diagnostics else None)
        token = current_diagnostics.set(scope)
        try:
            return self._execute(job, scope)
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
