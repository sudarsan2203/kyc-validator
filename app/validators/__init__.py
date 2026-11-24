"""Registry of validators.

The API looks validators up by name here. To support a new ID type,
write a Validator subclass and add it to REGISTRY. No route code changes.
"""

from app.validators.aadhaar import AadhaarValidator
from app.validators.base import ValidationResult, Validator
from app.validators.gstin import GstinValidator
from app.validators.ifsc import IfscValidator
from app.validators.pan import PanValidator

REGISTRY: dict[str, Validator] = {
    validator.id_type: validator
    for validator in (PanValidator(), AadhaarValidator(), GstinValidator(), IfscValidator())
}


def get_validator(id_type: str) -> Validator | None:
    """Return the validator for an ID type, or None if it is not supported."""
    return REGISTRY.get(id_type.lower())


def supported_types() -> list[str]:
    return sorted(REGISTRY)


__all__ = ["REGISTRY", "ValidationResult", "Validator", "get_validator", "supported_types"]
