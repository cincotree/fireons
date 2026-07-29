"""Generates synthetic (non-PII) CAS-shaped PDF fixtures for tests.

Run directly to regenerate all fixture files:
    uv run python tests/fixtures/generate_cas_fixture.py

These are NOT real CAS statements — no real folio, scheme, or holding data
is used anywhere in this repo. The layout (a "CAS as on" header line, then
AMC / Folio No blocks each followed by a scheme name, optional ISIN line,
and a units/NAV/market-value summary, with blank lines separating scheme
entries) has not yet been checked against a real CAMS/KFintech/MFCentral
CAS PDF — see the real-sample validation gate in statements/parsers/cas.py.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

TEST_CAS_PDF_PASSWORD = "Fireons-CAS-Test-1234"

FIXTURES_DIR = Path(__file__).parent

HEADER_LINES = [
    "CAMS CONSOLIDATED ACCOUNT STATEMENT",
    "",
    "CAS as on: 31-Mar-2025",
    "",
]

# Combined "Closing Balance / NAV / Market Value" summary line, with ISIN.
SCHEME_A_LINES = [
    "AMC: Alpha Mutual Fund",
    "Folio No: 1122334 / 0",
    "Alpha Bluechip Growth Fund",
    "ISIN: INF111A01234",
    "Closing Balance: 1234.567 NAV: 45.6789 Market Value: 56391.23",
    "",
]

# Three separate labeled lines, no ISIN (missing-ISIN case).
SCHEME_B_LINES = [
    "Folio No: 1122335 / 0",
    "Alpha Small Cap Fund - Direct Growth",
    "Closing Unit Balance: 500.000",
    "NAV as on 31-Mar-2025: 89.1234",
    "Market Value: 44561.70",
    "",
]

# Bare AMC header (no "AMC:" label) + columnar summary line.
SCHEME_C_LINES = [
    "Beta Mutual Fund",
    "Folio No: 9988776 / 0",
    "Beta Liquid Fund - Direct Growth",
    "ISIN: INF222B05678",
    "500.000000 250.1234 125061.70 (Value)",
    "",
]

# Zero-unit holding (fully redeemed, folio retained), combined summary line.
SCHEME_D_LINES = [
    "Folio No: 9988777 / 0",
    "Beta Redeemed Scheme - Growth",
    "ISIN: INF222B09999",
    "Closing Balance: 0.000 NAV: 10.0000 Market Value: 0.00",
    "",
]

# One scheme whose balance line is unparseable by any of the three summary
# variants — should be skipped with a warning, not fail the whole document.
UNPARSEABLE_SCHEME_LINES = [
    "Folio No: 5555555 / 0",
    "Gamma Unparseable Fund",
    "ISIN: INF333C01234",
    "This line has no recognizable balance data at all.",
    "",
]

VALID_CAS_LINES = (
    HEADER_LINES + SCHEME_A_LINES + SCHEME_B_LINES + SCHEME_C_LINES + SCHEME_D_LINES
)

CAS_WITH_UNPARSEABLE_SCHEME_LINES = VALID_CAS_LINES + UNPARSEABLE_SCHEME_LINES

COMBINED_VARIANT_ONLY_LINES = HEADER_LINES + SCHEME_A_LINES
LABELED_VARIANT_ONLY_LINES = HEADER_LINES + ["AMC: Alpha Mutual Fund"] + SCHEME_B_LINES
COLUMNAR_VARIANT_ONLY_LINES = HEADER_LINES + SCHEME_C_LINES

NO_HOLDINGS_LINES = [
    "SOME UNRELATED DOCUMENT",
    "This file is not a CAS statement.",
    "It has no AMC, folio, or scheme information at all.",
]

_REUPLOAD_SCHEME_LINES = [
    "AMC: Gamma Mutual Fund",
    "Folio No: 7777777 / 0",
    "Gamma Growth Fund",
    "ISIN: INF444D01234",
]

CAS_REUPLOAD_BEFORE_LINES = (
    ["CAMS CONSOLIDATED ACCOUNT STATEMENT", "", "CAS as on: 31-Mar-2025", ""]
    + _REUPLOAD_SCHEME_LINES
    + ["Closing Balance: 1000.000 NAV: 50.0000 Market Value: 50000.00", ""]
)

CAS_REUPLOAD_AFTER_LINES = (
    ["CAMS CONSOLIDATED ACCOUNT STATEMENT", "", "CAS as on: 30-Apr-2025", ""]
    + _REUPLOAD_SCHEME_LINES
    + ["Closing Balance: 1100.000 NAV: 55.0000 Market Value: 60500.00", ""]
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
        COMBINED_VARIANT_ONLY_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_combined_variant.pdf",
    )
    _write_encrypted(
        LABELED_VARIANT_ONLY_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_labeled_variant.pdf",
    )
    _write_encrypted(
        COLUMNAR_VARIANT_ONLY_LINES,
        TEST_CAS_PDF_PASSWORD,
        FIXTURES_DIR / "cas_columnar_variant.pdf",
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
