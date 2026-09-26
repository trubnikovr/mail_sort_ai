import argparse
import logging
from time import sleep

from mail_collector.bootstrap import build_synchronization_service
from mail_collector.mailboxes.models import MailboxAccount
from mail_collector.infrastructure.settings import Settings
from mail_collector.synchronization.service import MailboxSynchronizationService


logger = logging.getLogger(__name__)


def synchronize_once(service: MailboxSynchronizationService, settings: Settings) -> int:
    account = MailboxAccount(
        id=settings.mailbox_account_id,
        provider=settings.mailbox_provider,
        mailbox=settings.mailbox_source,
    )
    return service.synchronize(account)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect recent emails through the configured provider")
    parser.add_argument("--once", action="store_true", help="Synchronize once and exit")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    service = build_synchronization_service(settings)

    while True:
        try:
            count = synchronize_once(service, settings)
            logger.info("mailbox synchronization completed: discovered=%s", count)
        except Exception:
            logger.exception("mailbox synchronization failed")
            if arguments.once:
                raise

        if arguments.once:
            return
        sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
