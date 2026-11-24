"""Shared test setup.

All ID numbers used in the tests are made up. They follow the format rules
but were not taken from real documents.
"""

import os

# Point the app at a test database BEFORE importing it.
# CI sets TEST_DATABASE_URL to PostgreSQL. Locally it falls back to SQLite.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_kyc.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, config  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ApiKey  # noqa: E402

VALID_PAN = "AAAPA1234A"
VALID_AADHAAR = "234567890124"
VALID_GSTIN = "27AAAPA1234A1ZT"  # contains VALID_PAN
VALID_IFSC = "ABCD0123456"


@pytest.fixture(autouse=True)
def clean_state():
    """Give every test empty tables and a fresh rate limiter."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    auth.limiter.reset()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_key(db) -> str:
    """Create an API key in the database and return the raw key."""
    raw_key = auth.generate_key()
    db.add(ApiKey(name="test-client", key_hash=auth.hash_key(raw_key)))
    db.commit()
    return raw_key


@pytest.fixture
def headers(api_key) -> dict[str, str]:
    return {"X-API-Key": api_key}


@pytest.fixture
def admin_token(monkeypatch) -> str:
    monkeypatch.setattr(config, "ADMIN_TOKEN", "test-admin-token")
    return "test-admin-token"
