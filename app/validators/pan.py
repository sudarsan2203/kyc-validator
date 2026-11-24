"""PAN (Permanent Account Number) format check.

Format: 5 letters, 4 digits, 1 letter. Example shape: AAAPA1234A.
The 4th letter tells you what kind of holder the PAN belongs to.
"""

import re

from app.validators.base import Validator

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

HOLDER_TYPES = {
    "P": "Individual",
    "C": "Company",
    "H": "Hindu Undivided Family",
    "F": "Firm",
    "A": "Association of Persons",
    "T": "Trust",
    "B": "Body of Individuals",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government",
}


class PanValidator(Validator):
    id_type = "pan"

    def check(self, value: str) -> tuple[list[str], dict[str, str]]:
        if not PAN_PATTERN.match(value):
            return ["PAN must be 5 letters, then 4 digits, then 1 letter"], {}

        holder_code = value[3]
        if holder_code not in HOLDER_TYPES:
            return [f"4th character '{holder_code}' is not a valid PAN holder type"], {}

        return [], {"holder_type": HOLDER_TYPES[holder_code]}
