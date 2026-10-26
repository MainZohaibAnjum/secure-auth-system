from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine is the connection to PostgreSQL (it keeps a pool of connections ready)
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A factory that creates a new "session" (a conversation with the database)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Give each request its own session, and close it when the request ends."""
    with SessionLocal() as db:
        yield db
