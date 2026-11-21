from ingestion.parsers.deposits import try_parse_fd, try_parse_rd
from ingestion.parsers.loans import try_parse_loan_statement
from tests.evals.fixtures.generate_eval_fixtures import (
    FD_2026_07_LINES,
    HDFC_2026_07_LINES,
    HDFC_LOAN_2026_07_LINES,
    RD_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_loan_statement_reports_positive_outstanding_principal():
    facts = try_parse_loan_statement(_text(HDFC_LOAN_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "loan_statement"
    assert facts["source"] == "HDFC"
    assert facts["is_exhaustive"] is False
    holding = facts["holdings"][0]
    assert holding["institution"] == "HDFC"
    assert holding["identifier"] == "9988776655"
    assert holding["value"] == "350000.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-07-31"


def test_loan_statement_does_not_match_regular_bank_statement():
    assert try_parse_loan_statement(_text(HDFC_2026_07_LINES)) is None


def test_loan_statement_does_not_match_unrelated_document():
    assert try_parse_loan_statement(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_fd_parses_expected_facts():
    facts = try_parse_fd(_text(FD_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "deposit_statement"
    holding = facts["holdings"][0]
    assert holding["institution"] == "HDFC"
    assert holding["identifier"] == "5544332211"
    assert holding["instrument_type"] == "fd"
    assert holding["value"] == "428500.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-31"


def test_fd_does_not_match_rd_document():
    assert try_parse_fd(_text(RD_2026_07_LINES)) is None


def test_rd_parses_expected_facts():
    facts = try_parse_rd(_text(RD_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["institution"] == "ICICI"
    assert holding["identifier"] == "6677889900"
    assert holding["instrument_type"] == "rd"
    assert holding["value"] == "118500.00"
    assert holding["currency"] == "INR"
    assert facts["investor_name"] == "TEST USER"


def test_rd_does_not_match_fd_document():
    assert try_parse_rd(_text(FD_2026_07_LINES)) is None
