"""Synchronous SQLAlchemy engine and session factory helpers."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings, settings


def create_db_engine(app_settings: Settings = settings) -> Engine:
    return create_engine(
        app_settings.DATABASE_URL,
        echo=app_settings.DB_ECHO,
        pool_size=app_settings.DB_POOL_SIZE,
        max_overflow=app_settings.DB_POOL_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


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
