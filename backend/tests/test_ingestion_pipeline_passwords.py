from datetime import date

from ingestion.model import NetWorth
from ingestion.pipeline import ingest

FIXTURES_DIR = __import__("pathlib").Path(__file__).parent / "evals" / "fixtures"
CORRECT_PASSWORD = "Fireons-Eval-Test-1234"


def _empty() -> NetWorth:
    return NetWorth(as_of=None, reporting_currency="INR", positions={}, total="0")


def test_per_file_password_overrides_wrong_batch_password():
    hdfc = FIXTURES_DIR / "hdfc_2026_07.pdf"

    result = ingest(
        _empty(),
        [hdfc],
        password="definitely-wrong",
        passwords={"hdfc_2026_07.pdf": CORRECT_PASSWORD},
    )

    assert "Assets:Bank:HDFC:6789" in result.positions
    assert result.warnings == []


def test_falls_back_to_batch_password_when_no_per_file_entry():
    hdfc = FIXTURES_DIR / "hdfc_2026_07.pdf"

    result = ingest(_empty(), [hdfc], password=CORRECT_PASSWORD, passwords={})

    assert "Assets:Bank:HDFC:6789" in result.positions


def test_wrong_per_file_password_quarantines_only_that_file():
    hdfc = FIXTURES_DIR / "hdfc_2026_07.pdf"
    icici = FIXTURES_DIR / "icici_2026_07.pdf"

    result = ingest(
        _empty(),
        [hdfc, icici],
        passwords={
            "hdfc_2026_07.pdf": "wrong-password",
            "icici_2026_07.pdf": CORRECT_PASSWORD,
        },
    )

    assert "Assets:Bank:HDFC:6789" not in result.positions
    assert "Assets:Bank:ICICI:4321" in result.positions
    assert any("hdfc_2026_07.pdf" in w and "password" in w for w in result.warnings)
