from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from mail_sort_database.models import AiRequest, JobEvent
from mail_sort_database.session import session_scope
from mail_decision.processing.statistics.diagnostics import DiagnosticStore


class DatabaseDiagnosticStore(DiagnosticStore):
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def record(self, kind: str, values: dict) -> None:
        values = dict(values)
        model = {"step": JobEvent, "ai": AiRequest}[kind]
        for key in ("job_id", "run_id"):
            values[key] = UUID(values[key])
        with session_scope(self._sessions) as session:
            session.add(model(**values))
