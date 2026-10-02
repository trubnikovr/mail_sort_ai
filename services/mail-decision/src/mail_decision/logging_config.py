import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    log_dir = Path(__file__).resolve().parents[4] / "logs" / "mail-decision"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = TimedRotatingFileHandler(
        log_dir / "mail-sort.log", when="midnight", interval=1,
        backupCount=14, encoding="utf-8", delay=True,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler], force=True)
