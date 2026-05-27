"""Synchronous SQLAlchemy engine and session factory helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings, settings


def create_db_engine(app_settings: Settings = settings) -> Engine:
    engine_kwargs: dict[str, object] = {
        "echo": app_settings.DB_ECHO,
        "pool_pre_ping": True,
    }

    if not urlsplit(app_settings.DATABASE_URL).scheme.startswith("sqlite"):
        engine_kwargs["pool_size"] = app_settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = app_settings.DB_POOL_MAX_OVERFLOW

    return create_engine(app_settings.DATABASE_URL, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
