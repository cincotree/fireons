from ingestion.parsers.brokerage import try_parse_fidelity, try_parse_morgan_stanley_rsu
from tests.evals.fixtures.generate_eval_fixtures import (
    FIDELITY_2026_07_LINES,
    MORGAN_STANLEY_RSU_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_morgan_stanley_rsu_only_reads_vested_holdings_section():
    facts = try_parse_morgan_stanley_rsu(_text(MORGAN_STANLEY_RSU_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "brokerage_statement"
    assert len(facts["holdings"]) == 1
    holding = facts["holdings"][0]
    assert holding["identifier"] == "SAMPLETICK"
    assert holding["units"] == "25.000"
    assert holding["nav"] == "180.0000"
    assert holding["value"] == "4500.00"
    assert holding["currency"] == "USD"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-08-02"
    assert facts["investor_name"] == "TEST USER"


def test_morgan_stanley_rsu_does_not_match_unrelated_document():
    assert try_parse_morgan_stanley_rsu(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_fidelity_parses_expected_facts():
    facts = try_parse_fidelity(_text(FIDELITY_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "brokerage_statement"
    holding = facts["holdings"][0]
    assert holding["identifier"] == "GLOBEX"
    assert holding["units"] == "10.000"
    assert holding["nav"] == "350.0000"
    assert holding["value"] == "3500.00"
    assert holding["currency"] == "USD"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-08-02"
    assert facts["investor_name"] == "TEST USER"


def test_fidelity_does_not_match_morgan_stanley_document():
    assert try_parse_fidelity(_text(MORGAN_STANLEY_RSU_2026_07_LINES)) is None
