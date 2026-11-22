from ingestion.parsers.demat import try_parse_cdsl_consolidated_demat_cas, try_parse_demat_cas
from tests.evals.fixtures.generate_eval_fixtures import (
    CAMS_2026_07_LINES,
    NSDL_CDSL_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_demat_cas_parses_equity_reit_invit():
    facts = try_parse_demat_cas(_text(NSDL_CDSL_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "demat_cas"
    assert facts["source"] == "CDSL"
    assert facts["is_exhaustive"] is True
    assert facts["doc_issued_at"] == "2026-08-05"

    holdings = {h["identifier"]: h for h in facts["holdings"]}
    assert holdings["SAMPLESTK"]["instrument_type"] == "equity"
    assert holdings["SAMPLESTK"]["institution"] is None
    assert holdings["SAMPLESTK"]["units"] == "50.000"
    assert holdings["SAMPLESTK"]["nav"] == "2400.0000"
    assert holdings["SAMPLESTK"]["value"] == "120000.00"
    assert holdings["SAMPLESTK"]["as_of"] == "2026-07-31"

    assert holdings["SAMPLEREIT"]["instrument_type"] == "reit"
    assert holdings["SAMPLEREIT"]["value"] == "35000.00"

    assert holdings["SAMPLEINVIT"]["instrument_type"] == "invit"
    assert holdings["SAMPLEINVIT"]["value"] == "22000.00"


def test_demat_cas_does_not_match_cams_cas():
    assert try_parse_demat_cas(_text(CAMS_2026_07_LINES)) is None


def test_demat_cas_does_not_match_unrelated_document():
    assert try_parse_demat_cas(_text(UNKNOWN_DOCUMENT_LINES)) is None


# try_parse_cdsl_consolidated_demat_cas reads CDSL's real "HOLDING STATEMENT
# AS ON" table (a different, messier document from the synthetic
# "EQUITY HOLDINGS"/"REIT HOLDINGS" format above try_parse_demat_cas expects).
# An ETF's description is printed with the exact same "<AMC>#<AMC> MF-<scheme
# name>" naming convention as an open-ended mutual fund folio held in demat
# form ("NIPPON LIFE INDIA AM LTD#NIPPON INDIA MF-NIPPON INDIA ETF GOLD
# BEES") — confirmed on a real document that this was silently excluded
# entirely (treated as an unrepresentable demat-held mutual fund) even though
# an ETF trades on the exchange via its own ISIN just like a stock. Real
# holdings affected: Gold BEES, Nifty 50 BEES, Silver ETF — several lakh
# rupees combined, missing from net worth with no error, just a warning
# easy to miss.
CDSL_CONSOLIDATED_ETF_LINES = [
    "Central Depository Services (India) Limited",
    "CONSOLIDATED ACCOUNT STATEMENT (CAS) FOR SECURITIES HELD IN DEMAT",
    "HOLDING STATEMENT AS ON 30-07-2026",
    "ISIN Security Current Bal Frozen Bal Pledge Bal Pledge Setup Bal Free Bal Market Price Value",
    "INE000A00001 SAMPLE EQUITY LIMITED",
    "# EQUITY SHARES 10.000 -- -- -- 10.000 500.0000 5,000.00",
    "INF000B00002",
    "SAMPLE AMC LTD#SAMPLE",
    "MF-SAMPLE ETF GOLD BEES",
    "50.000 -- -- -- 50.000 100.0000 5,000.00",
    "INF000C00003",
    "SAMPLE AMC LTD#SAMPLE",
    "MF-SAMPLE ELSS TAX SAVER FUND-DIRECT PLAN",
    "20.000 -- -- -- 20.000 200.0000 4,000.00",
]


def test_cdsl_consolidated_demat_cas_captures_etf_despite_mf_naming_convention():
    facts = try_parse_cdsl_consolidated_demat_cas(_text(CDSL_CONSOLIDATED_ETF_LINES))
    assert facts is not None
    assert facts["document_type"] == "demat_cas"

    holdings = {h["identifier"]: h for h in facts["holdings"]}
    assert holdings["INE000A00001"]["instrument_type"] == "equity"
    # A plain company's instrument_name is the security's own name, shown
    # instead of a bare ISIN — cut at its LIMITED/LTD suffix.
    assert holdings["INE000A00001"]["instrument_name"] == "SAMPLE EQUITY LIMITED"

    # The ETF must be captured (as its own "etf" instrument_type — buried
    # under "equity" among two dozen ordinary stocks, it was findable in the
    # data but not in the UI, confirmed by the user), not excluded just
    # because its AMC naming text also contains "MF-" — and its
    # instrument_name must be the actual product name ("SAMPLE ETF GOLD
    # BEES"), not the fund HOUSE's own name ("SAMPLE AMC LTD", which precedes
    # it and has its own LTD suffix that would otherwise be picked up by
    # mistake), and with no leftover trailing numeric row data glued onto the
    # end.
    assert holdings["INF000B00002"]["instrument_type"] == "etf"
    assert holdings["INF000B00002"]["value"] == "5000.00"
    assert holdings["INF000B00002"]["instrument_name"] == "SAMPLE ETF GOLD BEES"

    # A genuine demat-held mutual fund (no "ETF" in its description) is still
    # correctly excluded — the fix must not swallow the real exclusion too.
    assert "INF000C00003" not in holdings
    assert any(
        "INF000C00003" in w and "not captured" in w for w in facts["warnings"]
    )
