from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .url import normalize_database_url


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_engine_from_url(database_url), expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
