"""Per-attempt diagnostic context shared by orchestration and the AI adapter."""
import logging
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


class DiagnosticStore(ABC):
    @abstractmethod
    def record(self, kind: str, values: dict[str, Any]) -> None:
        raise NotImplementedError


@dataclass
class DiagnosticScope:
    store: DiagnosticStore
    job_id: str
    run_id: str
    attempt: int
    step: str = "process"
    step_number: int = 0
    destinations: set[str] = field(default_factory=set)

    def record(self, kind: str, **values: Any) -> None:
        try:
            self.store.record(kind, dict(
                job_id=self.job_id, run_id=self.run_id, attempt=self.attempt,
                step=self.step, step_number=self.step_number, **values,
            ))
        except Exception as error:
            # Diagnostics must not replay an already committed business action.
            logging.getLogger(__name__).error(
                "diagnostic write failed: job_id=%s run_id=%s error_type=%s",
                self.job_id, self.run_id, type(error).__name__,
            )


current_diagnostics: ContextVar[DiagnosticScope | None] = ContextVar("diagnostics", default=None)
