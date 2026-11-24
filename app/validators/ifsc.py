"""IFSC (Indian Financial System Code) format check.

Format: 4 letters (bank), then the digit 0, then 6 letters or digits (branch).
"""

import re

from app.validators.base import Validator

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class IfscValidator(Validator):
    id_type = "ifsc"

    def check(self, value: str) -> tuple[list[str], dict[str, str]]:
        if not IFSC_PATTERN.match(value):
            return ["IFSC must be 4 letters, then 0, then 6 letters or digits"], {}

        return [], {"bank_code": value[:4], "branch_code": value[5:]}
