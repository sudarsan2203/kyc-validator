"""Verhoeff checksum, used for the last digit of an Aadhaar number.

It catches every single-digit typo and every swap of two neighbouring digits,
which the simpler Luhn checksum (used on bank cards) does not fully manage.

The algorithm keeps a running value `c`, starting at 0. For each digit, read
from right to left, it looks up a new `c` using two fixed tables:

- PERMUTATION scrambles the digit depending on its position.
- MULTIPLICATION combines the scrambled digit with the running value.

A number is valid when `c` ends at 0.
"""

MULTIPLICATION = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

PERMUTATION = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

INVERSE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def is_valid(number: str) -> bool:
    """Return True if `number` (digits only, check digit last) passes the checksum."""
    c = 0
    for position, digit in enumerate(reversed(number)):
        c = MULTIPLICATION[c][PERMUTATION[position % 8][int(digit)]]
    return c == 0


def check_digit(number: str) -> str:
    """Return the digit to append to `number` so that the result is valid."""
    c = 0
    for position, digit in enumerate(reversed(number)):
        # position + 1 because the check digit will take position 0.
        c = MULTIPLICATION[c][PERMUTATION[(position + 1) % 8][int(digit)]]
    return str(INVERSE[c])
