import argparse
import logging

from .commands import add_destination
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="mail-destination-setup")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Create an EWS folder and register a database destination")
    add.add_argument("--id", required=True, help="Stable ID used by classification")
    add.add_argument("--name", required=True, help="Human-readable destination name")
    add.add_argument("--mailbox", required=True, help="Folder path, e.g. Mail Sort/Sales")
    add.add_argument("--description", default="", help="Classification guidance")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    add_destination(
        settings,
        destination_id=arguments.id,
        name=arguments.name,
        mailbox=arguments.mailbox,
        description=arguments.description,
    )
    logging.info("Destination %s is ready at %s", arguments.id, arguments.mailbox)
