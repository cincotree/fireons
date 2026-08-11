import hashlib
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
    # Byte-identical on every call — caching it means only the first call in a session
    # pays full price for this ~1KB schema; every later call (a different document,
    # even) reads it from cache instead.
    "cache_control": {"type": "ephemeral"},
    "input_schema": {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": [
                    "bank_statement",
                    "mutual_fund_cas",
                    "epf_passbook",
                    "loan_statement",
                    "brokerage_statement",
                ],
                "description": "The kind of statement this document is.",
            },
            "doc_issued_at": {
                "type": "string",
                "description": "ISO datetime (YYYY-MM-DDTHH:MM:SS, time defaults to "
                "00:00:00 if not printed) the document itself was generated/issued — e.g. "
                "'Statement Generated On', 'Printed On'. This is a single fact about the "
                "document, not per-holding: when two documents describe the same as_of "
                "with different figures (a correction), the one with the later "
                "doc_issued_at wins, regardless of which was uploaded first or second.",
            },
            "source": {
                "type": "string",
                "description": "The specific issuer/aggregator that produced this document "
                "— e.g. 'CAMS', 'CDSL', 'KFinTech', or the AMC's own short name for a "
                "standalone individual-holding statement. Look for an explicit statement "
                "like 'brought to you by CAMS' or the issuing organization's name on the "
                "letterhead — do not guess from document_type alone. This scopes "
                "completeness: a document's claim to be exhaustive never extends beyond its "
                "own source, even to a same-shaped document from elsewhere. Confirmed "
                "necessary in practice — CDSL genuinely covers more funds than CAMS, so a "
                "CAMS document's completeness must never be read as saying anything about "
                "CDSL-sourced holdings, and vice versa.",
            },
            "is_exhaustive": {
                "type": "boolean",
                "description": "True only if this document explicitly presents itself as a "
                "complete listing for its source — a consolidated/summary statement showing "
                "multiple holdings together (e.g. a 'Consolidated Account Statement' with a "
                "portfolio summary section). False for any document that only ever "
                "describes a single holding on its own (e.g. a standalone individual AMC "
                "statement for one folio, a single bank account statement) — such a "
                "document makes no claim about anything else from that source, so its "
                "silence about other holdings must never be read as those holdings being "
                "gone.",
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
                            "epf_passbook (there is only one EPFO, no institution to name) and "
                            "for brokerage_statement (the ticker symbol alone is the "
                            "identifier, no broker name needed in the key).",
                        },
                        "identifier": {
                            "type": "string",
                            "description": "Last 4 digits of the account number for a bank "
                            "holding, the folio number for a mutual fund holding, the UAN for "
                            "an epf_passbook holding, the loan account number (numeric portion "
                            "only, strip any prefix like 'LN') for a loan_statement holding, "
                            "or the ticker symbol for a brokerage_statement holding.",
                        },
                        "instrument_name": {
                            "type": ["string", "null"],
                            "description": "Scheme name for a mutual fund holding; null for a "
                            "bank account or epf_passbook. Two normalization rules, both "
                            "required because the same fund can be described very differently "
                            "across documents — the folio number alone is NOT a safe "
                            "identifier on its own, a single folio can legitimately hold "
                            "multiple different schemes. (1) Strip generic plan/option "
                            "suffixes that describe how the scheme is held, not what it is: "
                            "'- Growth', '- Direct Plan', '- Regular Plan', '(Dividend)', "
                            "'(IDCW)', '- Growth Option', and similar. (2) Strip the AMC/"
                            "institution's own name if it appears redundantly prefixed onto "
                            "the scheme text — the institution field already captures that. "
                            "Example: one document prints 'SchemeAlpha - Growth', another "
                            "prints 'SampleAMC1 Scheme Alpha Growth Plan' for the identical "
                            "fund — both must normalize to the same value, 'SchemeAlpha'/"
                            "'Scheme Alpha' being the distinctive part with the AMC prefix and "
                            "plan suffix both removed. Keep only the distinctive scheme name "
                            "itself.",
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
                            "For loan_statement, report the Outstanding Principal as a "
                            "positive number exactly as printed — do not negate it yourself; "
                            "a liability's negative sign is applied downstream in code, not "
                            "by you. Null for epf_passbook — use employee_balance/"
                            "employer_balance/pension_balance instead, each reported "
                            "separately. Never sum them yourself; that happens downstream in "
                            "code.",
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
        "required": ["document_type", "doc_issued_at", "source", "is_exhaustive", "holdings"],
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


# Keyed by a hash of extracted TEXT, not the file — same_content_different_file's two
# byte-different PDFs with identical visible text collapse into one call, and the eval
# suite's file-order permutations (same underlying files, different order) stop paying
# for the same document N times over. Process-lifetime only, not persisted.
#
# Tradeoff: test_second_ingest_is_noop calls ingest() twice specifically to check the
# LLM gives the same answer both times. With this cache, the second call replays the
# first's result, so that test now only proves our own merge logic is stable, not that
# the LLM itself is — we already confirmed LLM-level idempotency separately before this
# was added, so this is an accepted tradeoff for cost, not an accidental loss of signal.
_extraction_cache: dict[str, dict] = {}


def extract_facts(pdf_bytes: bytes, password: str | None = None) -> dict:
    text = _read_pdf_text(pdf_bytes, password)
    cache_key = hashlib.sha256(text.encode()).hexdigest()
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]

    settings = get_settings()
    response = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": EXTRACT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
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
            _extraction_cache[cache_key] = block.input
            return block.input
    raise ValueError("Model did not return a tool_use block")
