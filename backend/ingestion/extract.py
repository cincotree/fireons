from io import BytesIO

from pypdf import PdfReader

from ingestion.config import get_settings
from ingestion.llm_client import get_client

# Fixture password for the eval corpus only (tests/evals/fixtures/generate_eval_fixtures.py).
# Real uploads carry a user-supplied password from the upload flow, not this constant —
# wiring that through is separate, later work; this scaffold only needs to read the eval
# fixtures to prove the extraction plumbing end to end.
_EVAL_FIXTURE_PASSWORD = "Fireons-Eval-Test-1234"

EXTRACT_TOOL = {
    "name": "record_extracted_facts",
    "description": "Record the raw facts extracted from a financial statement document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": ["bank_statement", "mutual_fund_cas", "epf_passbook"],
                "description": "The kind of statement this document is.",
            },
            "holdings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {
                            "type": ["string", "null"],
                            "description": "The institution's short common brand name — strip "
                            "legal-entity suffixes like 'BANK LIMITED', 'LTD', 'LIMITED', "
                            "'Bank' if a shorter brand name is used elsewhere in the document. "
                            "Examples: 'HDFC BANK LIMITED' -> 'HDFC'. 'SAMPLE AMC 1 - "
                            "SampleAMC1' (a long name and short code together) -> 'SampleAMC1', "
                            "always prefer the short code form when both appear. Do not "
                            "paraphrase or abbreviate beyond what these rules specify. Null for "
                            "epf_passbook (there is only one EPFO, no institution to name).",
                        },
                        "identifier": {
                            "type": "string",
                            "description": "Last 4 digits of the account number for a bank "
                            "holding, the folio number for a mutual fund holding, or the UAN "
                            "for an epf_passbook holding.",
                        },
                        "instrument_name": {
                            "type": ["string", "null"],
                            "description": "Scheme name for a mutual fund holding; null for a "
                            "bank account or epf_passbook. Strip generic plan/option suffixes "
                            "that describe how the scheme is held, not what it is: '- Growth', "
                            "'- Direct Plan', '- Regular Plan', '(Dividend)', '(IDCW)', '- "
                            "Growth Option', and similar. Example: 'SchemeAlpha - Growth' -> "
                            "'SchemeAlpha'. Keep the distinctive scheme name itself intact — "
                            "only drop the trailing plan/option descriptor.",
                        },
                        "units": {
                            "type": ["string", "null"],
                            "description": "Plain decimal string, no thousands separators — "
                            "e.g. a document printing '6,290.928' units means report "
                            "'6290.928'.",
                        },
                        "nav": {
                            "type": ["string", "null"],
                            "description": "Plain decimal string, no thousands separators.",
                        },
                        "value": {
                            "type": ["string", "null"],
                            "description": "Current value or closing balance as a plain "
                            "decimal string — no currency symbols, no thousands separators. "
                            "Null for epf_passbook — use employee_balance/employer_balance/"
                            "pension_balance instead, each reported separately. Never sum "
                            "them yourself; that happens downstream in code.",
                        },
                        "employee_balance": {
                            "type": ["string", "null"],
                            "description": "epf_passbook only — the Employee Balance column, "
                            "as a plain decimal string: no thousands separators (the document "
                            "may print Indian-style grouping like '2,29,892' — report the "
                            "number itself, '229892', not the printed digit grouping). Null "
                            "for other document types.",
                        },
                        "employer_balance": {
                            "type": ["string", "null"],
                            "description": "epf_passbook only — the Employer Balance column, "
                            "as a plain decimal string: no thousands separators (the document "
                            "may print Indian-style grouping like '2,29,892' — report the "
                            "number itself, '229892', not the printed digit grouping). Null "
                            "for other document types.",
                        },
                        "pension_balance": {
                            "type": ["string", "null"],
                            "description": "epf_passbook only — the Pension Balance (EPS) "
                            "column, as a plain decimal string: no thousands separators (the "
                            "document may print Indian-style grouping like '2,29,892' — report "
                            "the number itself, '229892', not the printed digit grouping). "
                            "Null for other document types.",
                        },
                        "currency": {"type": "string"},
                        "as_of": {
                            "type": "string",
                            "description": "ISO date (YYYY-MM-DD) this value is as of — the "
                            "holding's own NAV/valuation date if the document states one, not "
                            "just the statement period end. Exception for epf_passbook: use "
                            "the document's generation/print date (e.g. a 'Printed On' line), "
                            "NOT the 'Closing Balance as on <date>' label — that label is a "
                            "fiscal-year boundary the passbook software prints, not an actual "
                            "valuation event, and is routinely a future date relative to when "
                            "the document was generated when there were no transactions that "
                            "year (confirmed on a real EPFO passbook: 'Closing Balance as on "
                            "31/03/2027' printed on a document generated 09-08-2026).",
                        },
                    },
                    "required": ["identifier", "currency", "as_of"],
                },
            },
        },
        "required": ["document_type", "holdings"],
    },
}

EXTRACT_SYSTEM_PROMPT = (
    "You extract raw facts from financial statement documents. Report only what the "
    "document actually states — never compute, estimate, or infer a value it doesn't "
    "contain. If a document mentions unvested, potential, or contingent value that isn't "
    "actually owned yet, do not report it as a holding at all.\n\n"
    "institution and instrument_name are used as stable identity keys downstream — the "
    "same underlying account must always normalize to the exact same string, so follow "
    "the normalization rules in each field's schema description exactly and literally. "
    "Do not use your own judgment about what looks cleaner or more natural; apply the "
    "stated rules mechanically, the same way every time."
)


def _read_pdf_text(pdf_bytes: bytes, password: str | None) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    if reader.is_encrypted:
        reader.decrypt(password if password is not None else _EVAL_FIXTURE_PASSWORD)
    return "\n".join(page.extract_text() for page in reader.pages)


def extract_facts(pdf_bytes: bytes, password: str | None = None) -> dict:
    text = _read_pdf_text(pdf_bytes, password)
    settings = get_settings()
    response = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=EXTRACT_SYSTEM_PROMPT,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_extracted_facts"},
        messages=[
            {
                "role": "user",
                "content": f"Extract the facts from this statement:\n\n{text}",
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Model did not return a tool_use block")
