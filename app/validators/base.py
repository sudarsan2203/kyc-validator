"""The base class every ID validator inherits from."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

MAX_STORED_LENGTH = 32


def mask_value(value: str) -> str:
    """Hide everything except the last 4 characters.

    "ABCPE1234F" becomes "XXXXXX234F". Values of 4 characters or fewer are
    hidden completely. Long junk input is cut to MAX_STORED_LENGTH.
    """
    value = value[:MAX_STORED_LENGTH]
    if len(value) <= 4:
        return "X" * len(value)
    return "X" * (len(value) - 4) + value[-4:]


@dataclass
class ValidationResult:
    id_type: str
    is_valid: bool
    masked_value: str
    errors: list[str] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)


class Validator(ABC):
    """Base class for one type of ID.

    A subclass sets `id_type` and writes `check`. The shared steps
    (clean the input, run the check, mask the value) live in `validate`,
    so every ID type behaves the same way.
    """

    id_type: str

    def normalize(self, value: str) -> str:
        """Clean up user input: trim, uppercase, remove spaces."""
        return value.strip().upper().replace(" ", "")

    @abstractmethod
    def check(self, value: str) -> tuple[list[str], dict[str, str]]:
        """Check a normalized value.

        Returns (errors, details). An empty errors list means the value is valid.
        """

    def validate(self, raw_value: str) -> ValidationResult:
        value = self.normalize(raw_value)
        errors, details = self.check(value)
        return ValidationResult(
            id_type=self.id_type,
            is_valid=not errors,
            masked_value=mask_value(value),
            errors=errors,
            details=details,
        )
