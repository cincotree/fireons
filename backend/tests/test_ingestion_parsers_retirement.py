from ingestion.parsers.retirement import try_parse_epf, try_parse_nps
from tests.evals.fixtures.generate_eval_fixtures import (
    EPFO_2026_07_LINES,
    NPS_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_epf_uses_printed_on_date_not_fiscal_year_label():
    facts = try_parse_epf(_text(EPFO_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "epf_passbook"
    assert facts["doc_issued_at"] == "2026-07-31"
    assert facts["investor_name"] == "TEST USER"
    holding = facts["holdings"][0]
    assert holding["identifier"] == "100123456789"
    assert holding["employee_balance"] == "210000.00"
    assert holding["employer_balance"] == "190000.00"
    assert holding["pension_balance"] == "26000.00"
    assert holding["as_of"] == "2026-07-31"
    assert holding["currency"] == "INR"


def test_epf_does_not_match_unrelated_document():
    assert try_parse_epf(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_nps_parses_expected_facts():
    facts = try_parse_nps(_text(NPS_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "nps_statement"
    assert facts["doc_issued_at"] == "2026-08-02"
    assert facts["investor_name"] == "TEST USER"
    holding = facts["holdings"][0]
    assert holding["identifier"] == "110022334455"
    assert holding["instrument_name"] == "SchemeE"
    assert holding["units"] == "5000.000"
    assert holding["nav"] == "32.5000"
    assert holding["value"] == "162500.00"
    assert holding["as_of"] == "2026-07-31"


def test_nps_does_not_match_unrelated_document():
    assert try_parse_nps(_text(UNKNOWN_DOCUMENT_LINES)) is None
