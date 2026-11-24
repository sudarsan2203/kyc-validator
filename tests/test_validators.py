"""Unit tests for the validators. No database or HTTP involved."""

import pytest

from app.validators import get_validator, supported_types, verhoeff
from app.validators.base import mask_value
from app.validators.gstin import check_character, extract_pan
from tests.conftest import VALID_AADHAAR, VALID_GSTIN, VALID_IFSC, VALID_PAN

# ---------- Verhoeff ----------


@pytest.mark.parametrize(
    ("number", "expected"),
    [("236", "3"), ("12345", "1")],  # published examples of the algorithm
)
def test_verhoeff_check_digit_matches_published_examples(number, expected):
    assert verhoeff.check_digit(number) == expected
    assert verhoeff.is_valid(number + expected)


def test_verhoeff_catches_a_single_wrong_digit():
    assert not verhoeff.is_valid("2364")


def test_verhoeff_catches_two_swapped_digits():
    assert verhoeff.is_valid("123451")
    assert not verhoeff.is_valid("213451")


# ---------- PAN ----------


def test_valid_pan():
    result = get_validator("pan").validate(VALID_PAN)
    assert result.is_valid
    assert result.errors == []
    assert result.details == {"holder_type": "Individual"}


def test_pan_input_is_normalized():
    assert get_validator("pan").validate("  aaapa1234a ").is_valid


@pytest.mark.parametrize(
    "value",
    [
        "AAAPA1234",  # too short
        "AAAPA1234AB",  # too long
        "AAAP11234A",  # digit where a letter should be
        "AAAPA12X4A",  # letter where a digit should be
        "AAAPA-234A",  # symbol
    ],
)
def test_pan_with_wrong_shape_is_invalid(value):
    result = get_validator("pan").validate(value)
    assert not result.is_valid
    assert result.errors


def test_pan_with_unknown_holder_type_is_invalid():
    result = get_validator("pan").validate("AAAXA1234A")  # X is not a holder type
    assert not result.is_valid
    assert "holder type" in result.errors[0]


# ---------- Aadhaar ----------


def test_valid_aadhaar():
    assert get_validator("aadhaar").validate(VALID_AADHAAR).is_valid


@pytest.mark.parametrize("value", ["2345 6789 0124", "2345-6789-0124"])
def test_aadhaar_accepts_spaces_and_hyphens(value):
    assert get_validator("aadhaar").validate(value).is_valid


def test_aadhaar_with_wrong_checksum_is_invalid():
    result = get_validator("aadhaar").validate("234567890125")  # last digit changed
    assert not result.is_valid
    assert "Checksum" in result.errors[0]


@pytest.mark.parametrize("value", ["23456789012", "2345678901245", "23456789012A"])
def test_aadhaar_with_wrong_shape_is_invalid(value):
    assert not get_validator("aadhaar").validate(value).is_valid


@pytest.mark.parametrize("first_digit", ["0", "1"])
def test_aadhaar_cannot_start_with_0_or_1(first_digit):
    # Build a number with a correct checksum, so only the first-digit rule can fail.
    first_11 = first_digit + "2345678901"
    value = first_11 + verhoeff.check_digit(first_11)
    result = get_validator("aadhaar").validate(value)
    assert not result.is_valid
    assert "start with" in result.errors[0]


# ---------- IFSC ----------


def test_valid_ifsc():
    result = get_validator("ifsc").validate(VALID_IFSC)
    assert result.is_valid
    assert result.details == {"bank_code": "ABCD", "branch_code": "123456"}


@pytest.mark.parametrize(
    "value",
    [
        "ABCD1123456",  # 5th character must be 0
        "ABC00123456",  # bank code must be 4 letters
        "ABCD012345",  # too short
        "ABCD01234567",  # too long
    ],
)
def test_invalid_ifsc(value):
    assert not get_validator("ifsc").validate(value).is_valid


# ---------- GSTIN ----------


def test_valid_gstin():
    result = get_validator("gstin").validate(VALID_GSTIN)
    assert result.is_valid
    assert result.details["state_code"] == "27"


def test_gstin_details_do_not_expose_the_full_pan():
    result = get_validator("gstin").validate(VALID_GSTIN)
    assert result.details["pan"] == "XXXXXX234A"


def test_gstin_check_character():
    assert check_character(VALID_GSTIN[:14]) == VALID_GSTIN[14]


def test_gstin_with_wrong_check_character_is_invalid():
    result = get_validator("gstin").validate(VALID_GSTIN[:14] + "A")
    assert not result.is_valid
    assert result.errors == ["Check character does not match"]


def test_gstin_with_unknown_state_code_is_invalid():
    first_14 = "45" + VALID_GSTIN[2:14]
    result = get_validator("gstin").validate(first_14 + check_character(first_14))
    assert not result.is_valid
    assert "state code" in result.errors[0]


def test_gstin_with_invalid_embedded_pan_is_invalid():
    first_14 = "27" + "AAAXA1234A" + "1Z"  # X is not a PAN holder type
    result = get_validator("gstin").validate(first_14 + check_character(first_14))
    assert not result.is_valid
    assert "PAN" in result.errors[0]


def test_gstin_with_wrong_length_is_invalid():
    assert not get_validator("gstin").validate(VALID_GSTIN[:-1]).is_valid


def test_extract_pan_from_gstin():
    assert extract_pan(VALID_GSTIN) == VALID_PAN


# ---------- Masking and registry ----------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("AAAPA1234A", "XXXXXX234A"),
        ("ABCD", "XXXX"),
        ("AB", "XX"),
        ("", ""),
    ],
)
def test_mask_value(value, expected):
    assert mask_value(value) == expected


def test_mask_value_cuts_long_input():
    assert len(mask_value("9" * 100)) == 32


def test_result_never_contains_the_full_value():
    for id_type, value in [("pan", VALID_PAN), ("aadhaar", VALID_AADHAAR), ("gstin", VALID_GSTIN)]:
        result = get_validator(id_type).validate(value)
        assert value not in result.masked_value
        assert result.masked_value.endswith(value[-4:])


def test_registry():
    assert supported_types() == ["aadhaar", "gstin", "ifsc", "pan"]
    assert get_validator("PAN") is get_validator("pan")
    assert get_validator("passport") is None
