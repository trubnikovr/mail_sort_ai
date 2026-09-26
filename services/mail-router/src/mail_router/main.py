import argparse
import logging

from .bootstrap import build_worker
from .infrastructure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one queued route")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    logging.info("router starting: worker_id=%s provider=%s mode=%s", settings.worker_id, settings.mailbox_provider, "once" if arguments.once else "continuous")
    worker = build_worker(settings)
    if arguments.once:
        worker.run_once()
        logging.info("router single cycle finished")
    else:
        worker.run_forever(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
