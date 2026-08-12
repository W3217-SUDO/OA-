from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.legacy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _set_read_only_session(dbapi_connection, _connection_record) -> None:
    """Prevent accidental mutations while the parity layer is being captured."""
    if settings.legacy_read_only:
        cursor = dbapi_connection.cursor()
        cursor.execute("SET IMPLICIT_TRANSACTIONS OFF")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
