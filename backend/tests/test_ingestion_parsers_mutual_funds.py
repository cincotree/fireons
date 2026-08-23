from ingestion.parsers.mutual_funds import (
    try_parse_cams_cas,
    try_parse_cams_kfintech_summary,
    try_parse_cdsl_mutual_fund_cas,
    try_parse_navi_account_statement,
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


# Regression fixtures for two real, confirmed duplicate-position bugs found by
# testing against actual documents (CAS_CAMS.pdf / CAS_KFinTech.pdf / a
# standalone Navi statement): the identical real-world fund, read from two or
# three different document formats, silently produced two or three different
# account keys instead of one — CAMS's transactional CAS prints the folio
# suffix with a space ("FOLIO500 / 1") and its scheme text unwrapped, while
# the KFinTech summary table prints the same folio with no space
# ("FOLIO500/1") and wraps its scheme description across lines right at a
# hyphen ("Plan-\nGrowth"), which becomes "Plan- Growth" once lines are
# joined with a space.
CAMS_REAL_SBI_LINES = [
    "This Consolidated Account Statement is brought to you by CAMS and lists holdings.",
    "SBI Mutual Fund",
    "PAN: SAMPLEPAN1Z KYC: OK  PAN: OK",
    "CODE1-SBI Sample Nifty Fund-Direct Plan-",
    "Growth (Non-Demat) - ISIN: INF000A00000(Advisor: XYZ) Registrar : CAMS",
    "Folio No: FOLIO500 / 1",
    "Test Investor",
    " Opening Unit Balance: 100.000",
    "NAV on 31-Jul-2026: INR 50.0000 Market Value on 31-Jul-2026: INR 5000.00",
    "Closing Unit Balance: 100.000 Total Cost Value: 4000.00",
    "Statement Generated On: 02-Aug-2026",
]

KFIN_SUMMARY_SBI_LINES = [
    "The Consolidated Account Summary is brought to you as an investor",
    "friendly initiative by CAMS and KFintech, and lists the balances.",
    "Consolidated Account Summary As on 31-Jul-2026",
    "FOLIO500/1 5,000.00CODE1 - SBI Sample Nifty Fund-Direct Plan-Growth",
    "100.000 31-Jul-2026 50.0000 CAMSINF000A00000 4000.000",
]


def test_cams_and_kfintech_summary_agree_on_same_fund_despite_formatting_differences():
    """A real folio suffix that prints with a space in CAMS ("FOLIO500 / 1")
    but without one in KFinTech ("FOLIO500/1"), and a scheme name that wraps
    at a hyphen in KFinTech's narrower table but not in CAMS's, must still
    reconcile to the exact same account identity — otherwise the pipeline
    treats them as two unrelated positions and double-counts the same
    holding (confirmed happening for real folios 19702068, 4840120/55, and
    22953612/46)."""
    cams = try_parse_cams_cas(_text(CAMS_REAL_SBI_LINES))
    kfin = try_parse_cams_kfintech_summary(_text(KFIN_SUMMARY_SBI_LINES))
    assert cams is not None
    assert kfin is not None

    cams_holding = cams["holdings"][0]
    kfin_holding = kfin["holdings"][0]

    assert cams_holding["identifier"] == kfin_holding["identifier"] == "FOLIO500/1"
    assert (
        cams_holding["instrument_name"]
        == kfin_holding["instrument_name"]
        == "SBI Sample Nifty Fund-Direct Plan-Growth"
    )
    assert cams_holding["institution"] == kfin_holding["institution"] == "SBI Mutual Fund"


NAVI_STATEMENT_SBI_LINES = [
    "Account Statement",
    "Folio Number : FOLIO500/1",
    "Statement Date : 02-Aug -2026",
    "Investor Name : Test Investor",
    "Thank you for Investing in Navi Mutual Fund !",
    "PORTFOLIO SUMMARY",
    "Scheme NAV Nav Date Unit Balance Current Value",
    "50.0000 100.000 5,000.00SBI Sample Nifty Fund - Direct Plan - Growth 4,000.0031-Jul-2026 0.00",
]


def test_navi_statement_normalizes_scheme_hyphens_same_as_cams_kfintech():
    """try_parse_navi_account_statement extracts its scheme name independently
    of try_parse_cams_cas/try_parse_cams_kfintech_summary (a completely
    different document layout), so fixing hyphen-whitespace normalization in
    the two CAMS-family parsers didn't fix it here too — confirmed as a real
    bug: the same real Navi fund (folio 9778840737) got a third, different
    instrument_name once the other two started stripping spaces around
    hyphens and this parser didn't. Must produce the identical normalized
    name a CAMS/KFinTech read of the same fund would (see
    test_cams_and_kfintech_summary_agree_on_same_fund_despite_formatting_differences)."""
    navi = try_parse_navi_account_statement(_text(NAVI_STATEMENT_SBI_LINES))
    assert navi is not None
    holding = navi["holdings"][0]
    assert holding["identifier"] == "FOLIO500/1"
    assert holding["instrument_name"] == "SBI Sample Nifty Fund-Direct Plan-Growth"
