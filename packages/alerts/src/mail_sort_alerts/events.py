from dataclasses import dataclass, field
from enum import StrEnum


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AlertEvent:
    deduplication_key: str
    source: str
    title: str
    message: str
    severity: AlertSeverity = AlertSeverity.CRITICAL
    context: dict[str, str | int | float | bool | None] = field(default_factory=dict)
