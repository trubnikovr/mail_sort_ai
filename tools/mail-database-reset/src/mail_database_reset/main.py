import argparse
import logging
from os import environ, getenv
from pathlib import Path

from sqlalchemy import text

from mail_sort_database.session import create_engine_from_url


TABLES_TO_CLEAR = (
    "ai_requests",
    "job_events",
    "audit_logs",
    "jobs",
    "email_records",
    "mailbox_cursors",
    "ai_daily_usage",
    "sorting_rules",
    "destinations",
)


def _load_local_env() -> None:
    env_file = Path(__file__).resolve().parents[4] / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip():
            environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clear Mail Sort application data while preserving the database schema."
    )
    parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_local_env()
    database_url = getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is not set and was not found in the project .env file")

    engine = create_engine_from_url(database_url)
    try:
        database = engine.url.database or "<unknown>"
        host = engine.url.host or "localhost"
        port = engine.url.port or 5432
        print(f"Target database: {database} at {host}:{port}")
        print("This removes all rows from:")
        print("  " + ", ".join(TABLES_TO_CLEAR))
        print("The alembic_version table and mailbox contents will not be changed.")
        try:
            confirmation = input(f'Type the database name "{database}" to continue: ').strip()
        except EOFError:
            confirmation = ""
        if confirmation != database:
            print("Confirmation did not match; database was not changed.")
            return

        table_list = ", ".join(f'"{table}"' for table in TABLES_TO_CLEAR)
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY"))
        print("Mail Sort database data cleared.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
