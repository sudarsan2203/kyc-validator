"""API-key management (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import generate_key, hash_key, require_admin
from app.database import get_db
from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyCreated

router = APIRouter(tags=["api keys"])


@router.post(
    "/api-keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_api_key(body: ApiKeyCreate, db: Session = Depends(get_db)):
    """Create an API key. The key is shown once here and cannot be read back later."""
    raw_key = generate_key()
    api_key = ApiKey(name=body.name, key_hash=hash_key(raw_key))
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return ApiKeyCreated(id=api_key.id, name=api_key.name, api_key=raw_key)
