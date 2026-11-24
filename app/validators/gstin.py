"""GSTIN (Goods and Services Tax Identification Number) format check.

A GSTIN has 15 characters:

    27  AAAPA1234A  1  Z  5
    |   |           |  |  |
    |   |           |  |  check character
    |   |           |  always "Z"
    |   |           registration number for this PAN in this state
    |   the holder's PAN
    state code
"""

import re

from app.validators.base import Validator, mask_value
from app.validators.pan import PanValidator

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[1-9A-Z]Z[0-9A-Z]$")

# 01-38 are states and union territories. 97 is "Other Territory",
# 99 is "Centre Jurisdiction".
STATE_CODES = {f"{n:02d}" for n in range(1, 39)} | {"97", "99"}

# Each character stands for a number: "0" is 0 ... "9" is 9, "A" is 10 ... "Z" is 35.
CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def check_character(first_14: str) -> str:
    """Work out the 15th character of a GSTIN from the first 14.

    Going from left to right, multiply each character's number by 1, 2, 1, 2 ...
    Split each product into (product // 36) + (product % 36) and add them all up.
    The check character is whatever brings the total up to a multiple of 36.
    """
    total = 0
    for position, char in enumerate(first_14):
        factor = 2 if position % 2 else 1
        product = CHARSET.index(char) * factor
        total += product // 36 + product % 36
    return CHARSET[(36 - total % 36) % 36]


def extract_pan(gstin: str) -> str:
    """Return the PAN embedded in a GSTIN (characters 3 to 12)."""
    return gstin[2:12]


class GstinValidator(Validator):
    id_type = "gstin"

    def check(self, value: str) -> tuple[list[str], dict[str, str]]:
        if not GSTIN_PATTERN.match(value):
            return ["GSTIN must be 15 characters: state code, PAN, entity number, Z, check character"], {}

        errors = []

        state_code = value[:2]
        if state_code not in STATE_CODES:
            errors.append(f"'{state_code}' is not a valid state code")

        pan = extract_pan(value)
        pan_errors, _ = PanValidator().check(pan)
        if pan_errors:
            errors.append("Characters 3 to 12 are not a valid PAN")

        if check_character(value[:14]) != value[14]:
            errors.append("Check character does not match")

        if errors:
            return errors, {}
        return [], {"state_code": state_code, "pan": mask_value(pan)}
