import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from mail_sort_database.models import Base
from mail_sort_database.url import normalize_database_url


config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    if not os.environ.get("DATABASE_URL"):
        project_root = Path(__file__).resolve().parents[3]
        env_file = project_root / ".env"
        if env_file.exists():
            for raw_line in env_file.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if separator and key.strip() == "DATABASE_URL":
                    os.environ["DATABASE_URL"] = value.strip().strip('"').strip("'")
                    break
    try:
        return normalize_database_url(os.environ["DATABASE_URL"])
    except KeyError as error:
        raise RuntimeError("DATABASE_URL is required to run migrations") from error


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
