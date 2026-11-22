from datetime import date

import pytest

from scraping.normalize import (
    classify_kind,
    content_hash,
    derive_status,
    normalize_name,
    parse_address,
    parse_validity,
)
from scraping.types import (
    ParseError,
    ProfessionalKind,
    ProfessionType,
    RegistrationStatus,
    ScrapedRegistration,
)


def make_record(**overrides) -> ScrapedRegistration:
    values = dict(
        registration_number="INA000000001",
        name="Example Adviser",
        kind=ProfessionalKind.INDIVIDUAL,
        profession_type=ProfessionType.INVESTMENT_ADVISER,
        valid_from=date(2022, 12, 22),
        valid_until=None,
        validity_raw="Dec 22, 2022 - Perpetual",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        address_raw="1 Road, Mumbai, Maharashtra, 400001",
        email="a@example.com",
        phone="910000000001",
        contact_person="A Person",
        source_url="https://example.test/list",
        attributes={},
    )
    values.update(overrides)
    return ScrapedRegistration(**values)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Dec 22, 2022 - Perpetual", (date(2022, 12, 22), None)),
        ("Dec 22, 2022 - perpetual", (date(2022, 12, 22), None)),
        ("Jan 1,2020 - Dec 31, 2025", (date(2020, 1, 1), date(2025, 12, 31))),
        ("  Mar 05, 2019   -   Mar 04, 2024 ", (date(2019, 3, 5), date(2024, 3, 4))),
        ("January 05, 2019 - Perpetual", (date(2019, 1, 5), None)),
    ],
)
def test_parse_validity_accepts_known_shapes(raw, expected):
    assert parse_validity(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [None, "", "Perpetual", "Sometime in 2020", "Dec 22, 2022", "Dec 32, 2022 - Perpetual",
     "Dec 31, 2025 - Jan 01, 2020"],
)
def test_parse_validity_rejects_unrecognised_text_loudly(raw):
    with pytest.raises(ParseError):
        parse_validity(raw)


@pytest.mark.parametrize(
    "address, expected",
    [
        ("Unit 1, Sample Plaza, MUMBAI, MAHARASHTRA, 400001", ("Mumbai", "Maharashtra", "400001")),
        (
            "5 Street, NAGPUR CITY, MAHARASHTRA, NAGPUR, MAHARASHTRA, 440022",
            ("Nagpur", "Maharashtra", "440022"),
        ),
        ("1 Lane, Chennai, tamil nadu, 600001", ("Chennai", "Tamil Nadu", "600001")),
        ("Plot 9, Test Colony, 110001", (None, None, "110001")),
        ("12 Test Road, DELHI, DELHI, 110001", (None, "Delhi", "110001")),
        ("Somewhere, Pune, Maharashtra 411001", ("Pune", "Maharashtra", "411001")),
        ("12 Foo St, Mumbai Maharashtra 400001", (None, None, "400001")),
        ("Somewhere unknown", (None, None, None)),
        ("", (None, None, None)),
        (None, (None, None, None)),
        ("1 Road, Bhubaneswar, Orissa, 751001", ("Bhubaneswar", "Odisha", "751001")),
    ],
)
def test_parse_address_extracts_city_state_pincode_or_none(address, expected):
    assert parse_address(address) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Example Advisers Private Limited", ProfessionalKind.FIRM),
        ("Sample Wealth LLP", ProfessionalKind.FIRM),
        ("1 Finance Private Limited", ProfessionalKind.FIRM),
        ("Asha Fictional", ProfessionalKind.INDIVIDUAL),
        ("Ravi Kumar Imaginary", ProfessionalKind.INDIVIDUAL),
    ],
)
def test_classify_kind(name, expected):
    assert classify_kind(name) == expected


def test_normalize_name_is_case_and_punctuation_insensitive():
    assert normalize_name("  Mehta & Sons,  (P) Ltd. ") == "mehta sons p ltd"
    assert normalize_name("MEHTA sons p LTD") == "mehta sons p ltd"


def test_derive_status_expired_only_when_end_date_has_passed():
    today = date(2026, 1, 1)
    assert derive_status(None, today) == RegistrationStatus.ACTIVE
    assert derive_status(date(2026, 1, 1), today) == RegistrationStatus.ACTIVE
    assert derive_status(date(2025, 12, 31), today) == RegistrationStatus.EXPIRED


def test_content_hash_is_stable_and_sensitive_to_field_changes():
    assert content_hash(make_record()) == content_hash(make_record())
    assert content_hash(make_record()) != content_hash(make_record(email="b@example.com"))
    assert content_hash(make_record()) != content_hash(make_record(attributes={"fax": "1"}))
