from ingestion.parsers.mutual_funds import (
    try_parse_cams_cas,
    try_parse_cdsl_mutual_fund_cas,
    try_parse_standalone_amc_statement,
)
from tests.evals.fixtures.generate_eval_fixtures import (
    CAMS_2026_07_LINES,
    CAMS_2026_07_MIXED_NAV_LINES,
    CDSL_CAS_2026_07_LINES,
    NSDL_CDSL_2026_07_LINES,
    SAMPLEAMC1_FOLIO001_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_cams_cas_parses_both_folios():
    facts = try_parse_cams_cas(_text(CAMS_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "mutual_fund_cas"
    assert facts["source"] == "CAMS"
    assert facts["is_exhaustive"] is True
    assert facts["doc_issued_at"] == "2026-08-02"
    holdings = {h["identifier"]: h for h in facts["holdings"]}
    assert holdings["FOLIO001"]["institution"] == "SampleAMC1"
    assert holdings["FOLIO001"]["instrument_name"] == "SchemeAlpha"
    assert holdings["FOLIO001"]["units"] == "100.000"
    assert holdings["FOLIO001"]["nav"] == "50.0000"
    assert holdings["FOLIO001"]["value"] == "5000.00"
    assert holdings["FOLIO001"]["as_of"] == "2026-07-31"
    assert holdings["FOLIO002"]["institution"] == "SampleAMC2"
    assert holdings["FOLIO002"]["instrument_name"] == "SchemeBeta"


def test_cams_cas_holdings_carry_independent_nav_dates():
    facts = try_parse_cams_cas(_text(CAMS_2026_07_MIXED_NAV_LINES))
    assert facts is not None
    holdings = {h["identifier"]: h for h in facts["holdings"]}
    assert holdings["FOLIO001"]["as_of"] == "2026-07-29"
    assert holdings["FOLIO002"]["as_of"] == "2026-07-31"


def test_cams_cas_does_not_match_cdsl_demat_cas():
    assert try_parse_cams_cas(_text(NSDL_CDSL_2026_07_LINES)) is None


def test_cams_cas_does_not_match_unrelated_document():
    assert try_parse_cams_cas(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_standalone_amc_statement_reconciles_to_same_key_as_cams():
    facts = try_parse_standalone_amc_statement(_text(SAMPLEAMC1_FOLIO001_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "mutual_fund_cas"
    assert facts["source"] == "SampleAMC1"
    assert facts["is_exhaustive"] is False
    holding = facts["holdings"][0]
    assert holding["institution"] == "SampleAMC1"
    assert holding["identifier"] == "FOLIO001"
    assert holding["instrument_name"] == "SchemeAlpha"
    assert holding["value"] == "5000.00"
    assert holding["as_of"] == "2026-07-31"


def test_standalone_amc_statement_does_not_match_cams_cas():
    assert try_parse_standalone_amc_statement(_text(CAMS_2026_07_LINES)) is None


def test_standalone_amc_statement_unknown_amc_defers_to_llm():
    unknown_amc_lines = [
        "BRAND NEW FUND HOUSE PRIVATE LIMITED",
        "Account Statement",
        "PAN : SAMPLEPAN1Z",
        "Folio No : FOLIO999",
        "Scheme : SchemeZeta - Growth",
        "Closing Units : 10.000",
        "NAV on 31-Jul-2026: INR 10.0000 Market Value on 31-Jul-2026: INR 100.00",
        "Statement Generated On: 03-Aug-2026",
    ]
    assert try_parse_standalone_amc_statement(_text(unknown_amc_lines)) is None


def test_cdsl_mutual_fund_cas_reconciles_to_same_key_as_cams():
    facts = try_parse_cdsl_mutual_fund_cas(_text(CDSL_CAS_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "mutual_fund_cas"
    assert facts["source"] == "CDSL"
    assert facts["is_exhaustive"] is True
    holding = facts["holdings"][0]
    assert holding["institution"] == "SampleAMC1"
    assert holding["identifier"] == "FOLIO001"
    assert holding["instrument_name"] == "SchemeAlpha"
    assert holding["units"] == "100.000"
    assert holding["nav"] == "50.0000"
    assert holding["value"] == "5000.00"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-08-05"


def test_cdsl_mutual_fund_cas_does_not_match_cdsl_demat_cas():
    assert try_parse_cdsl_mutual_fund_cas(_text(NSDL_CDSL_2026_07_LINES)) is None


def test_cdsl_mutual_fund_cas_does_not_match_cams_cas():
    assert try_parse_cdsl_mutual_fund_cas(_text(CAMS_2026_07_LINES)) is None
