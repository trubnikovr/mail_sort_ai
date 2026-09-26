from collections.abc import Callable
from datetime import UTC, datetime, timedelta


class RecentMailPolicy:
    """Specification limiting collection to messages from the last two days."""

    _LOOKBACK = timedelta(days=2)

    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))

    def imap_since_criterion(self) -> str:
        return self._cutoff().strftime("%d-%b-%Y")

    def _cutoff(self) -> datetime:
        return self._now() - self._LOOKBACK
