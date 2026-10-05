import argparse
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from mail_sort_database.models import Destination
from mail_sort_database.session import create_session_factory, session_scope
from .destination_defaults import DESTINATIONS, DestinationRecord

from .commands import add_destination
from .provisioners import provision_catalog
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="mail-destination-setup")
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser(
        "sync", help="Initialize missing destinations, then create folders from PostgreSQL"
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
        sessions = create_session_factory(settings.database_url)
        with session_scope(sessions) as session:
            for destination in DESTINATIONS:
                statement = insert(Destination).values(
                    id=destination.id,
                    account_id=account_id,
                    name=destination.name,
                    instruction=destination.instruction,
                    mailbox=destination.mailbox,
                    is_active=destination.enabled,
                    use_for_ai=destination.use_for_ai,
                ).on_conflict_do_nothing(index_elements=[Destination.id])
                session.execute(statement)
            records = session.scalars(
                select(Destination).where(
                    Destination.account_id == account_id,
                    Destination.is_active.is_(True),
                )
            ).all()
            destinations = tuple(
                DestinationRecord(
                    id=item.id,
                    name=item.name,
                    instruction=item.instruction,
                    mailbox=item.mailbox,
                    enabled=item.is_active,
                    use_for_ai=item.use_for_ai,
                )
                for item in records
            )
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
