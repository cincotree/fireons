from datetime import date

from scraping.sources.sebi_ria import parse_listing_page
from scraping.types import ProfessionalKind, ProfessionType
from tests.fixtures.generate_sebi_fixtures import FIXTURES_DIR, GOOD_RECORDS, render_ajax_page, render_first_page


def load(name: str):
    return parse_listing_page((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_first_page_markup_is_parsed_with_pagination_info():
    page = load("listing_page_1.html")

    assert page.expected_total == 8
    assert page.page_size == 3
    assert page.parse_errors == 0
    assert [r.registration_number for r in page.records] == [
        "INA000000001",
        "INA000000002",
        "INA000000003",
    ]


def test_ajax_markup_is_parsed_and_entities_are_decoded():
    page = load("ajax_page_2.html")

    wealth = next(r for r in page.records if r.registration_number == "INA000000004")
    assert wealth.email == "hello@example.com"
    assert wealth.name == "Sample Wealth LLP"
    assert wealth.kind == ProfessionalKind.FIRM


def test_record_with_unparseable_validity_counts_as_parse_error_not_crash():
    page = load("ajax_page_2.html")

    assert page.parse_errors == 1
    assert "INA000000005" not in [r.registration_number for r in page.records]
    assert len(page.records) == 2


def test_full_record_fields_are_normalized():
    record = load("listing_page_1.html").records[0]

    assert record.name == "Example Advisers Private Limited"
    assert record.profession_type == ProfessionType.INVESTMENT_ADVISER
    assert record.valid_from == date(2022, 12, 22)
    assert record.valid_until is None
    assert record.validity_raw == "Dec 22, 2022 - Perpetual"
    assert (record.city, record.state, record.pincode) == ("Mumbai", "Maharashtra", "400001")
    assert record.email == "compliance@example.com"
    assert record.phone == "910000000001"
    assert record.contact_person == "Test Person One"
    assert record.attributes == {
        "fax": "910000000002",
        "correspondence_address": "Unit 1, Sample Plaza, Sample Road, MUMBAI, MAHARASHTRA, 400001",
    }
    assert record.source_url.startswith("https://www.sebi.gov.in/")


def test_missing_optional_fields_become_none():
    record = load("listing_page_1.html").records[1]

    assert record.email is None
    assert record.phone is None
    assert record.valid_until == date(2024, 3, 4)
    assert record.attributes == {}


def test_email_is_lowercased():
    record = load("listing_page_1.html").records[2]

    assert record.email == "ravi.imaginary@example.com"


def test_page_without_records_yields_empty_result():
    page = parse_listing_page("<html><body><p>nothing here</p></body></html>")

    assert page.records == []
    assert page.parse_errors == 0
    assert page.expected_total is None


def test_ifsc_registration_numbers_are_accepted():
    record = {**GOOD_RECORDS[0], "reg": "INAIFSC99999"}

    for render in (render_first_page, render_ajax_page):
        page = parse_listing_page(render([record], 1, 1, 1))

        assert page.parse_errors == 0
        assert [r.registration_number for r in page.records] == ["INAIFSC99999"]


def test_unknown_registration_number_formats_are_flagged_not_guessed():
    for bad in ("INB000000001", "INA12345", "ina000000001x", ""):
        page = parse_listing_page(render_ajax_page([{**GOOD_RECORDS[0], "reg": bad}], 1, 1, 1))

        assert page.records == []
        assert page.parse_errors == 1


def test_registration_number_is_uppercased():
    page = parse_listing_page(render_ajax_page([{**GOOD_RECORDS[0], "reg": "ina000000001"}], 1, 1, 1))

    assert [r.registration_number for r in page.records] == ["INA000000001"]
