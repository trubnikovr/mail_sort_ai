import argparse
import logging
from .bootstrap import build_worker
from .infrastructure.settings import Settings
from .infrastructure.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one queued route")
    arguments = parser.parse_args()
    configure_logging()
    settings = Settings.from_environment()
    logger.info("router starting: worker_id=%s mode=%s", settings.worker_id, "once" if arguments.once else "continuous")
    worker = build_worker(settings)
    if arguments.once:
        worker.run_once()
        logger.info("router single cycle finished")
    else:
        worker.run_forever(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
