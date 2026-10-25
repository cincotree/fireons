from ingestion.parsers.insurance import try_parse_term_insurance, try_parse_ulip
from ingestion.parsers.sgb import try_parse_sgb_confirmation
from tests.evals.fixtures.generate_eval_fixtures import (
    SGB_CONFIRMATION_2026_07_LINES,
    TERM_INSURANCE_2026_07_LINES,
    ULIP_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_sgb_confirmation_uses_consideration_amount_not_units_times_price():
    facts = try_parse_sgb_confirmation(_text(SGB_CONFIRMATION_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "sgb_confirmation"
    holding = facts["holdings"][0]
    assert holding["identifier"] == "SGB2028SeriesIV"
    assert holding["units"] == "10"
    assert holding["value"] == "62000.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-06"
    assert facts["investor_name"] == "TEST USER"


def test_sgb_confirmation_does_not_match_unrelated_document():
    assert try_parse_sgb_confirmation(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_ulip_uses_surrender_value_not_fund_value():
    facts = try_parse_ulip(_text(ULIP_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "insurance_policy"
    assert facts["source"] == "SampleLife"
    holding = facts["holdings"][0]
    assert holding["institution"] == "SampleLife"
    assert holding["identifier"] == "7788990011"
    assert holding["value"] == "185000.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-31"


def test_ulip_does_not_match_term_insurance():
    assert try_parse_ulip(_text(TERM_INSURANCE_2026_07_LINES)) is None


def test_term_insurance_contributes_zero_holdings():
    facts = try_parse_term_insurance(_text(TERM_INSURANCE_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "insurance_policy"
    assert facts["holdings"] == []
    assert facts["warnings"] == []


def test_term_insurance_does_not_match_ulip():
    assert try_parse_term_insurance(_text(ULIP_2026_07_LINES)) is None
