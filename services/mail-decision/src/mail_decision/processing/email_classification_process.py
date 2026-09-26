import logging
from time import perf_counter

from .context import ClaimedEmailJob, ProcessingContext, ProcessingOutcome
from .steps.interface import ProcessingStep


logger = logging.getLogger(__name__)


class EmailClassificationProcess:
    """Runs the ordered steps that classify one claimed email job."""

    def __init__(self, steps: list[ProcessingStep]) -> None:
        self._steps = steps

    def execute(self, job: ClaimedEmailJob) -> ProcessingOutcome:
        context = ProcessingContext(job=job)
        started = perf_counter()
        for number, step in enumerate(self._steps, start=1):
            name = type(step).__name__
            step_started = perf_counter()
            logger.info("step started: job_id=%s step=%s/%s name=%s", job.id, number, len(self._steps), name)
            try:
                step.execute(context)
            except Exception as error:
                logger.error(
                    "step failed: job_id=%s name=%s duration_seconds=%.2f error_type=%s",
                    job.id, name, perf_counter() - step_started, type(error).__name__,
                )
                raise
            logger.info(
                "step finished: job_id=%s name=%s duration_seconds=%.2f",
                job.id, name, perf_counter() - step_started,
            )
        if context.outcome is None:
            raise RuntimeError("Classification steps completed without an outcome")
        logger.info(
            "classification result saved and route queued: job_id=%s status=%s destination_id=%s "
            "confidence=%s source=%s duration_seconds=%.2f",
            job.id, context.outcome.status, context.outcome.destination_id,
            context.outcome.confidence, context.outcome.source, perf_counter() - started,
        )
        return context.outcome
