"""Validation endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models import ApiKey, ValidationLog
from app.schemas import (
    BatchRequest,
    BatchResponse,
    GstinPanMatchRequest,
    GstinPanMatchResponse,
    ValidateRequest,
    ValidationResponse,
)
from app.validators import ValidationResult, get_validator, supported_types
from app.validators.base import mask_value
from app.validators.gstin import extract_pan

router = APIRouter(tags=["validation"])


def add_log(db: Session, api_key: ApiKey, result: ValidationResult) -> None:
    """Queue an audit-log row. Only the masked value is stored."""
    db.add(
        ValidationLog(
            api_key_id=api_key.id,
            id_type=result.id_type,
            masked_value=result.masked_value,
            is_valid=result.is_valid,
        )
    )


@router.get("/id-types")
def list_id_types() -> list[str]:
    """List the ID types this API can validate."""
    return supported_types()


# The two fixed paths below are declared before /validate/{id_type}.
# FastAPI matches routes in order, so otherwise "batch" would be read as an id_type.


@router.post("/validate/batch", response_model=BatchResponse)
def validate_batch(
    body: BatchRequest,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """Validate up to 100 IDs of mixed types in one call."""
    results = []
    for item in body.items:
        validator = get_validator(item.id_type)
        if validator is None:
            # An unknown type fails that one item, not the whole batch.
            results.append(
                ValidationResult(
                    id_type=item.id_type,
                    is_valid=False,
                    masked_value=mask_value(item.value.strip()),
                    errors=[f"Unsupported id_type. Supported: {supported_types()}"],
                )
            )
            continue
        result = validator.validate(item.value)
        add_log(db, api_key, result)
        results.append(result)

    db.commit()  # one commit for the whole batch

    valid = sum(1 for result in results if result.is_valid)
    return BatchResponse(
        total=len(results),
        valid=valid,
        invalid=len(results) - valid,
        results=[ValidationResponse(**asdict(result)) for result in results],
    )


@router.post("/validate/gstin-pan-match", response_model=GstinPanMatchResponse)
def gstin_pan_match(
    body: GstinPanMatchRequest,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """Check that a GSTIN and a PAN are both valid and belong together.

    Every GSTIN contains its holder's PAN, so the two can be compared.
    """
    gstin_validator = get_validator("gstin")
    pan_validator = get_validator("pan")

    gstin_result = gstin_validator.validate(body.gstin)
    pan_result = pan_validator.validate(body.pan)
    add_log(db, api_key, gstin_result)
    add_log(db, api_key, pan_result)
    db.commit()

    both_valid = gstin_result.is_valid and pan_result.is_valid
    same_pan = extract_pan(gstin_validator.normalize(body.gstin)) == pan_validator.normalize(body.pan)
    return GstinPanMatchResponse(
        gstin_valid=gstin_result.is_valid,
        pan_valid=pan_result.is_valid,
        match=both_valid and same_pan,
    )


@router.post("/validate/{id_type}", response_model=ValidationResponse)
def validate_one(
    id_type: str,
    body: ValidateRequest,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """Validate one ID. `id_type` is one of: pan, aadhaar, gstin, ifsc."""
    validator = get_validator(id_type)
    if validator is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Unsupported id_type '{id_type}'. Supported: {supported_types()}",
        )

    result = validator.validate(body.value)
    add_log(db, api_key, result)
    db.commit()
    return ValidationResponse(**asdict(result))
