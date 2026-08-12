from ingestion.parsers.bank_accounts import try_parse_chase, try_parse_hdfc, try_parse_icici
from tests.evals.fixtures.generate_eval_fixtures import (
    CHASE_2026_07_LINES,
    HDFC_2026_07_LINES,
    HDFC_JOINT_2026_07_LINES,
    HDFC_LOAN_2026_07_LINES,
    ICICI_2026_07_LINES,
    PPF_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_hdfc_parses_expected_facts():
    facts = try_parse_hdfc(_text(HDFC_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "bank_statement"
    assert facts["is_exhaustive"] is False
    assert facts["source"] == "HDFC"
    assert facts["investor_name"] == "MR. TEST USER"
    assert facts["doc_issued_at"] == "2026-07-31"
    holding = facts["holdings"][0]
    assert holding["institution"] == "HDFC"
    assert holding["identifier"] == "6789"
    assert holding["instrument_type"] is None
    assert holding["value"] == "150000.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-31"


def test_hdfc_ppf_variant_sets_instrument_type():
    facts = try_parse_hdfc(_text(PPF_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["instrument_type"] == "ppf"
    assert holding["identifier"] == "8776"
    assert holding["value"] == "192600.00"


def test_hdfc_joint_account_keeps_both_names():
    facts = try_parse_hdfc(_text(HDFC_JOINT_2026_07_LINES))
    assert facts is not None
    assert facts["investor_name"] == "MR. TEST USER & MRS. SPOUSE USER"
    assert facts["holdings"][0]["identifier"] == "8877"
    assert facts["holdings"][0]["value"] == "105000.00"


def test_hdfc_defers_loan_statement_to_its_own_parser():
    assert try_parse_hdfc(_text(HDFC_LOAN_2026_07_LINES)) is None


def test_hdfc_does_not_match_unrelated_document():
    assert try_parse_hdfc(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_icici_parses_expected_facts():
    facts = try_parse_icici(_text(ICICI_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["institution"] == "ICICI"
    assert holding["identifier"] == "4321"
    assert holding["value"] == "80000.00"
    assert holding["currency"] == "INR"
    assert facts["doc_issued_at"] == "2026-07-31"
    assert facts["investor_name"] == "TEST USER"


def test_icici_does_not_match_hdfc_text():
    assert try_parse_icici(_text(HDFC_2026_07_LINES)) is None


def test_chase_parses_expected_facts_with_us_currency_and_date_order():
    facts = try_parse_chase(_text(CHASE_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["institution"] == "Chase"
    assert holding["identifier"] == "1234"
    assert holding["value"] == "1000.00"
    assert holding["currency"] == "USD"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-07-31"
    assert facts["investor_name"] == "TEST USER"


def test_chase_does_not_match_hdfc_text():
    assert try_parse_chase(_text(HDFC_2026_07_LINES)) is None
