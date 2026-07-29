"""Generates synthetic (non-PII) CAS-shaped PDF fixtures for tests.

Run directly to regenerate all fixture files:
    uv run python tests/fixtures/generate_cas_fixture.py

These are NOT real CAS statements — no real folio, scheme, holding, or
investor data is used anywhere in this repo. The layout (a "Consolidated
Account Summary" / "As on <date>" header, then one row per holding: folio
number + market value + scheme code/name on one or more lines, followed by a
closing line of unit balance / NAV date / NAV / registrar+ISIN / cost value)
mirrors the structure of a real CAMS-issued "Consolidated Account Summary"
PDF, confirmed by manually inspecting one (outside this repo, never
committed) while fixing this parser. AMC names used below (HDFC, SBI,
Aditya Birla Sun Life, Tata) are real, publicly known fund-house names —
matching the parser's actual AMC-alias list is the point — but every folio
number, scheme code, unit balance, NAV, and rupee amount is made up.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

TEST_CAS_PDF_PASSWORD = "Fireons-CAS-Test-1234"

FIXTURES_DIR = Path(__file__).parent


def _header_lines(as_on: str, doc_id: str = "TEST0001") -> list[str]:
    return [
        f"CAMSCASWS-{doc_id} Version:V1.0 Test",
        "Consolidated Account Summary",
        f"As on {as_on}",
        "Page 1 of 1",
        "Market ValueFolio No.",
        "(INR)",
        "Scheme Name Unit Balance",
        "NAV Date NAV Registrar",
        "(INR)",
        "ISIN Cost Value",
        "(INR)",
    ]


# Known AMC (Aditya Birla Sun Life), CAMS registrar, scheme text wraps
# across two lines.
SCHEME_A_LINES = [
    "1234567 56,391.23T001 - Aditya Birla Sun Life Test Bluechip",
    "Fund - Growth-Direct Plan (Non-Demat)",
    "1,234.567 31-Mar-2025 45.6789 CAMSINF999A01111 50,000.000",
]

# Known AMC (HDFC), KFintech registrar, zero-balance holding (fully
# redeemed, folio retained), single-line scheme text.
SCHEME_B_LINES = [
    "7654321/0 0.00T002 - HDFC Test Liquid Fund - Direct Plan - Growth (Non-Demat)",
    "0.000 31-Mar-2025 350.1234 KFINTECHINF999B02222 0.000",
]

# Known AMC (SBI), CAMS registrar, Indian-style comma grouping, scheme text
# wraps across three lines to stress multi-line accumulation.
SCHEME_C_LINES = [
    "9988776 1,25,061.70T003 - SBI Test Small Cap",
    "Fund - Regular",
    "Plan - Growth (Demat)",
    "500.000 31-Mar-2025 250.1234 CAMSINF999C03333 1,00,000.000",
]

# AMC not in the parser's known-alias list — exercises the "guess from the
# first two words, flag a per-holding warning" fallback path.
SCHEME_D_LINES = [
    "5551111 12,345.60T004 - Zephyr Capital Test",
    "Fund - Growth (Non-Demat)",
    "100.000 31-Mar-2025 123.456 CAMSINF999D04444 10,000.000",
]

# Starts a holding but never provides a valid closing line before EOF —
# should be skipped with a warning, not fail the whole document.
UNPARSEABLE_SCHEME_LINES = [
    "9999999 1,000.00T005 - Broken Test Fund - This scheme has no",
    "recognizable balance detail line at all, just prose.",
]

VALID_CAS_LINES = (
    _header_lines("31-Mar-2025")
    + SCHEME_A_LINES
    + SCHEME_B_LINES
    + SCHEME_C_LINES
    + SCHEME_D_LINES
)

CAS_WITH_UNPARSEABLE_SCHEME_LINES = VALID_CAS_LINES + UNPARSEABLE_SCHEME_LINES

NO_HOLDINGS_LINES = [
    "SOME UNRELATED DOCUMENT",
    "This file is not a CAS statement.",
    "It has no folio or scheme holding information at all.",
]

_REUPLOAD_SCHEME_DESCRIPTOR = [
    "T006 - Tata Test Growth Fund - Direct Plan -",
    "Growth (Non-Demat)",
]

CAS_REUPLOAD_BEFORE_LINES = (
    _header_lines("31-Mar-2025", "TEST0002")
    + [f"5551234 50,000.00{_REUPLOAD_SCHEME_DESCRIPTOR[0]}"] + _REUPLOAD_SCHEME_DESCRIPTOR[1:]
    + ["1,000.000 31-Mar-2025 50.0000 CAMSINF999E05555 45,000.000"]
)

CAS_REUPLOAD_AFTER_LINES = (
    _header_lines("30-Apr-2025", "TEST0002")
    + [f"5551234 60,500.00{_REUPLOAD_SCHEME_DESCRIPTOR[0]}"] + _REUPLOAD_SCHEME_DESCRIPTOR[1:]
    + ["1,100.000 30-Apr-2025 55.0000 CAMSINF999E05555 49,500.000"]
)


def _render_pdf_bytes(lines: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(595, 842))
    y = 800
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 18
    pdf.save()
    return buffer.getvalue()


def _write_encrypted(lines: list[str], password: str, path: Path) -> None:
    plain_bytes = _render_pdf_bytes(lines)
    reader = PdfReader(BytesIO(plain_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password)
    with open(path, "wb") as fh:
        writer.write(fh)


def generate_all() -> None:
    _write_encrypted(VALID_CAS_LINES, TEST_CAS_PDF_PASSWORD, FIXTURES_DIR / "cas_valid.pdf")
    _write_encrypted(
        CAS_WITH_UNPARSEABLE_SCHEME_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_with_unparseable_scheme.pdf",
    )
    _write_encrypted(
        NO_HOLDINGS_LINES, TEST_CAS_PDF_PASSWORD, FIXTURES_DIR / "cas_no_holdings.pdf"
    )
    _write_encrypted(
        CAS_REUPLOAD_BEFORE_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_reupload_before.pdf",
    )
    _write_encrypted(
        CAS_REUPLOAD_AFTER_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_reupload_after.pdf",
    )


if __name__ == "__main__":
    generate_all()
    print(f"Fixtures written to {FIXTURES_DIR}")
