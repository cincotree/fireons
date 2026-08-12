from ingestion.parsers.demat import try_parse_demat_cas
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
