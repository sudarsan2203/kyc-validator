"""Aadhaar number format check.

Format: 12 digits. The first digit is never 0 or 1.
The last digit is a Verhoeff checksum of the first 11.
"""

from app.validators import verhoeff
from app.validators.base import Validator


class AadhaarValidator(Validator):
    id_type = "aadhaar"

    def normalize(self, value: str) -> str:
        # Aadhaar is often written as "1234 5678 9012" or "1234-5678-9012".
        return super().normalize(value).replace("-", "")

    def check(self, value: str) -> tuple[list[str], dict[str, str]]:
        if not (value.isascii() and value.isdigit() and len(value) == 12):
            return ["Aadhaar must be exactly 12 digits"], {}

        if value[0] in "01":
            return ["Aadhaar cannot start with 0 or 1"], {}

        if not verhoeff.is_valid(value):
            return ["Checksum digit does not match"], {}

        return [], {}
