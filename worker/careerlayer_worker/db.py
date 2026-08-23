from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from careerlayer_api.settings import get_settings


@lru_cache
def _engine() -> Engine:
    """A synchronous engine, deliberately.

    The API is async because it is IO-bound and serves many short requests. The worker runs
    one long CPU-bound job at a time under RQ's forking model, where async buys nothing and
    costs a second driver and a second set of connection semantics to reason about.
    """
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "+psycopg")
    return create_engine(url, pool_pre_ping=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = sessionmaker(_engine(), expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
