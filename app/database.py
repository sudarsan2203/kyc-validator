"""Database connection and session handling."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config

# SQLite only allows a connection to be used by the thread that created it.
# FastAPI runs requests on a thread pool, so that check is turned off for SQLite.
connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Parent class for all database models."""


def get_db():
    """Give each request its own session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
