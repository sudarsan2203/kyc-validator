"""API-key authentication and rate limiting."""

import hashlib
import math
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import ApiKey
from app.rate_limiter import SlidingWindowRateLimiter

limiter = SlidingWindowRateLimiter(config.RATE_LIMIT_REQUESTS, config.RATE_LIMIT_WINDOW_SECONDS)


def generate_key() -> str:
    """Create a new random API key."""
    return "kyc_" + secrets.token_urlsafe(32)


def hash_key(raw_key: str) -> str:
    """Hash a key for storage, so a leaked database does not leak usable keys.

    Plain SHA-256 is enough here because the key is long and random.
    (Passwords are different: they are guessable and need a slow hash like bcrypt.)
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def require_api_key(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Dependency: find the caller's API key, or reject the request."""
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key header")

    api_key = db.scalar(
        select(ApiKey).where(ApiKey.key_hash == hash_key(x_api_key), ApiKey.is_active)
    )
    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    if not limiter.allow(api_key.id):
        wait = math.ceil(limiter.retry_after(api_key.id))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Rate limit exceeded",
            headers={"Retry-After": str(wait)},
        )
    return api_key


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Dependency: only allow callers that send the admin token."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Key creation is disabled: ADMIN_TOKEN is not set on the server",
        )
    # compare_digest takes the same time whether or not the strings match,
    # so the response time does not leak how many characters were right.
    if not secrets.compare_digest((x_admin_token or "").encode(), config.ADMIN_TOKEN.encode()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin token")
