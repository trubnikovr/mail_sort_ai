import argparse
import logging

from mail_sort_repositories import DestinationRepository

from .commands import add_destination
from .provisioners import provision_catalog
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="mail-destination-setup")
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser(
        "sync", help="Create enabled destination folders from the code catalog"
    )
    sync.add_argument("--account", help="Account ID; defaults to MAILBOX_ACCOUNT_ID")
    add = commands.add_parser("add", help="Create an EWS folder and register a database destination")
    add.add_argument("--id", required=True, help="Stable ID used by classification")
    add.add_argument("--name", required=True, help="Human-readable destination name")
    add.add_argument("--mailbox", required=True, help="Folder path, e.g. Mail Sort/Sales")
    add.add_argument("--description", default="", help="Classification guidance")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    if arguments.command == "sync":
        account_id = arguments.account or settings.mailbox_account_id
        destinations = DestinationRepository(account_id).active_for_account(account_id)
        logging.info("Provisioning %s destination folders for account %s",
                     len(destinations), account_id)
        provision_catalog(settings, destinations)
    elif arguments.command == "add":
        add_destination(
            settings,
            destination_id=arguments.id,
            name=arguments.name,
            mailbox=arguments.mailbox,
            description=arguments.description,
        )
        logging.info("Destination %s is ready at %s", arguments.id, arguments.mailbox)
