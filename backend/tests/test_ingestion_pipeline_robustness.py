from pathlib import Path

import ingestion.pipeline as pipeline_module
from ingestion.model import NetWorth
from ingestion.pipeline import ingest

FIXTURES_DIR = Path(__file__).parent / "evals" / "fixtures"
CORRECT_PASSWORD = "Fireons-Eval-Test-1234"


def _empty() -> NetWorth:
    return NetWorth(as_of=None, reporting_currency="INR", positions={}, total="0")


def test_incomplete_extraction_result_quarantines_that_file_only(monkeypatch):
    """A malformed tool-use response (missing a required key despite the schema
    asking for it) must not crash the whole batch with a raw KeyError — the
    schema's 'required' list is a prompt-level request, not an enforced
    guarantee, and this has happened in practice."""
    hdfc = FIXTURES_DIR / "hdfc_2026_07.pdf"
    icici = FIXTURES_DIR / "icici_2026_07.pdf"

    real_route_extract = pipeline_module.route_extract

    def flaky_route_extract(pdf_bytes: bytes, password: str | None = None) -> dict:
        facts = real_route_extract(pdf_bytes, password)
        if facts.get("source") == "HDFC" or (
            facts["holdings"] and facts["holdings"][0].get("institution") == "HDFC"
        ):
            del facts["document_type"]
        return facts

    monkeypatch.setattr(pipeline_module, "route_extract", flaky_route_extract)

    result = ingest(_empty(), [hdfc, icici], password=CORRECT_PASSWORD)

    assert "Assets:Bank:HDFC:6789" not in result.positions
    assert "Assets:Bank:ICICI:4321" in result.positions
    assert any("hdfc_2026_07.pdf" in w and "incomplete" in w for w in result.warnings)


def test_null_doc_issued_at_quarantines_that_file_only(monkeypatch):
    """doc_issued_at is schema-documented as nullable only for 'unrecognized'
    documents (already filtered out earlier) — but nothing enforces the model
    actually honoring that for every other type, and datetime.fromisoformat(None)
    crashes with a TypeError if it slips through. Confirmed happening in
    practice (same underlying class of issue as the missing-key case)."""
    hdfc = FIXTURES_DIR / "hdfc_2026_07.pdf"
    icici = FIXTURES_DIR / "icici_2026_07.pdf"

    real_route_extract = pipeline_module.route_extract

    def flaky_route_extract(pdf_bytes: bytes, password: str | None = None) -> dict:
        facts = real_route_extract(pdf_bytes, password)
        if facts.get("source") == "HDFC" or (
            facts["holdings"] and facts["holdings"][0].get("institution") == "HDFC"
        ):
            facts["doc_issued_at"] = None
        return facts

    monkeypatch.setattr(pipeline_module, "route_extract", flaky_route_extract)

    result = ingest(_empty(), [hdfc, icici], password=CORRECT_PASSWORD)

    assert "Assets:Bank:HDFC:6789" not in result.positions
    assert "Assets:Bank:ICICI:4321" in result.positions
    assert any("hdfc_2026_07.pdf" in w and "incomplete" in w for w in result.warnings)
