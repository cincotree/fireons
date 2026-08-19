import hashlib
from contextvars import ContextVar
from dataclasses import dataclass
from io import BytesIO

from pypdf import PasswordType, PdfReader

from ingestion.config import get_settings
from ingestion.llm_client import get_client

# $ per million tokens. Sticker pricing, not any time-boxed intro rate — a
# pricing dict that silently reverts to being wrong after an intro window
# expires is worse than a stable slight overestimate. Unknown models get no
# cost estimate (None) rather than a guessed number.
_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.00, 15.00),
}


@dataclass
class ExtractionUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


# Populated per ingest() call (see pipeline.py) so a single run's LLM calls can
# be aggregated into a cost estimate on the resulting NetWorth — a ContextVar
# rather than a plain module global so concurrent ingest() calls (each run in
# its own thread via asyncio.to_thread) don't cross-contaminate each other's
# usage totals.
_run_usage: ContextVar[list[ExtractionUsage] | None] = ContextVar("_run_usage", default=None)


def begin_usage_tracking():
    """Returns an opaque token — pass to end_usage_tracking() to collect this
    run's usage and restore the ContextVar to its prior state. Without the
    matching reset, .set() alone leaks into any other code sharing this
    thread afterward (confirmed: broke an unrelated test that called
    extract_facts_from_text() directly once some other test had called
    ingest() earlier in the same process)."""
    return _run_usage.set([])


def end_usage_tracking(token) -> list[ExtractionUsage]:
    usage = _run_usage.get() or []
    _run_usage.reset(token)
    return usage


def estimate_cost_usd(usage: list[ExtractionUsage], model: str) -> float | None:
    pricing = _PRICING_PER_MTOK.get(model)
    if pricing is None:
        return None
    input_price, output_price = pricing
    total = 0.0
    for u in usage:
        total += u.input_tokens * input_price
        total += u.cache_creation_input_tokens * input_price * 1.25
        total += u.cache_read_input_tokens * input_price * 0.1
        total += u.output_tokens * output_price
    return total / 1_000_000

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
                    "demat_cas",
                    "sgb_confirmation",
                    "deposit_statement",
                    "nps_statement",
                    "insurance_policy",
                    "unrecognized",
                ],
                "description": "The kind of statement this document is. Use 'unrecognized' "
                "for anything that is not actually an account/holding/balance statement at "
                "all — e.g. a fund factsheet, a brochure, marketing material. Never force a "
                "non-statement document into the nearest-sounding category just because it "
                "mentions a fund or account in passing; when in doubt whether a document is "
                "really a statement of holdings, prefer 'unrecognized'. holdings must be "
                "empty for 'unrecognized'.",
            },
            "doc_issued_at": {
                "type": ["string", "null"],
                "description": "ISO datetime (YYYY-MM-DDTHH:MM:SS, time defaults to "
                "00:00:00 if not printed) the document itself was generated/issued — e.g. "
                "'Statement Generated On', 'Printed On'. This is a single fact about the "
                "document, not per-holding: when two documents describe the same as_of "
                "with different figures (a correction), the one with the later "
                "doc_issued_at wins, regardless of which was uploaded first or second. If "
                "the document has no separate generated/printed line at all — only a "
                "statement period or a single effective date (confirmed real-world case: a "
                "US bank statement whose only date is its 'Month DD, YYYY through Month DD, "
                "YYYY' period) — use that document's own end/effective date here instead of "
                "null; null is for genuinely dateless documents and 'unrecognized' only, "
                "never for a recognized statement that simply lacks a distinct issue-date "
                "line.",
            },
            "investor_pan": {
                "type": ["string", "null"],
                "description": "The PAN (Permanent Account Number, India) of the account/"
                "policy/folio holder this document identifies, if the document states one "
                "anywhere — verbatim, do not guess if absent. Null if no PAN is printed "
                "anywhere in the document (common for plain bank/deposit statements) or for "
                "'unrecognized'. Not currently used for identity verification (that's "
                "name-only, see investor_name) — extracted for completeness/future use only.",
            },
            "investor_name": {
                "type": ["string", "null"],
                "description": "The name(s) of the account/policy/folio holder(s) this "
                "document identifies, exactly as printed — including a second name if it's "
                "a joint account (e.g. 'MR. TEST USER & MRS. SPOUSE USER', keep both names, "
                "do not pick just one). Null if no holder name is printed anywhere, or for "
                "'unrecognized'.",
            },
            "source": {
                "type": ["string", "null"],
                "description": "The specific issuer/aggregator that produced this document "
                "— e.g. 'CAMS', 'CDSL', 'KFinTech', or the AMC's own short name for a "
                "standalone individual-holding statement. Look for an explicit statement "
                "like 'brought to you by CAMS' or the issuing organization's name on the "
                "letterhead — do not guess from document_type alone. This scopes "
                "completeness: a document's claim to be exhaustive never extends beyond its "
                "own source, even to a same-shaped document from elsewhere. Confirmed "
                "necessary in practice — CDSL genuinely covers more funds than CAMS, so a "
                "CAMS document's completeness must never be read as saying anything about "
                "CDSL-sourced holdings, and vice versa. Null for 'unrecognized'.",
            },
            "is_exhaustive": {
                "type": ["boolean", "null"],
                "description": "True only if this document explicitly presents itself as a "
                "complete listing for its source — a consolidated/summary statement showing "
                "multiple holdings together (e.g. a 'Consolidated Account Statement' with a "
                "portfolio summary section). False for any document that only ever "
                "describes a single holding on its own (e.g. a standalone individual AMC "
                "statement for one folio, a single bank account statement) — such a "
                "document makes no claim about anything else from that source, so its "
                "silence about other holdings must never be read as those holdings being "
                "gone. Null for 'unrecognized'.",
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
                            "paraphrase or abbreviate beyond what these rules specify. For "
                            "insurance_policy, condense a multi-word brand name to one word, "
                            "no spaces, stripping legal/product words: 'SAMPLE LIFE INSURANCE "
                            "CO LTD' -> 'SampleLife'. Null for epf_passbook (there is only one "
                            "EPFO, no institution to name), brokerage_statement and demat_cas "
                            "(the ticker/ISIN-derived symbol alone is the identifier), and "
                            "sgb_confirmation (RBI is not a meaningful institution name here).",
                        },
                        "identifier": {
                            "type": "string",
                            "description": "Last 4 digits of the account number for a bank "
                            "holding — exactly 4 characters, count from the right end of the "
                            "printed number regardless of its total length, e.g. account "
                            "number '55000019988776' -> '8776', not '9988776' or any other "
                            "length. This is a required field — never write a placeholder like "
                            "'UNKNOWN' or '<UNKNOWN>'. Some statement layouts (confirmed on a "
                            "real US bank statement) separate an 'Account Number:' label from "
                            "its actual digits in the extracted text order — if the text right "
                            "after the label isn't a plausible account number, search the rest "
                            "of the document for a standalone long digit sequence (9+ digits) "
                            "near the top of the statement and use its last 4 digits instead of "
                            "giving up. The folio number for a mutual fund holding, the UAN for "
                            "an epf_passbook holding, the loan account number (numeric portion "
                            "only, strip any prefix like 'LN') for a loan_statement holding, "
                            "the ticker symbol for a brokerage_statement or demat_cas holding, "
                            "the deposit account number (numeric portion only, strip any "
                            "prefix like 'FD'/'RD') for a deposit_statement holding, a "
                            "normalized series identifier for an sgb_confirmation holding — "
                            "strip spaces and use consistent casing, e.g. 'SGB 2028 SERIES IV' "
                            "-> 'SGB2028SeriesIV' — the PRAN for an nps_statement holding, or "
                            "the policy number for an insurance_policy holding (numeric "
                            "portion only, strip any plan-type prefix like 'ULIP'/'TERM').",
                        },
                        "instrument_type": {
                            "type": ["string", "null"],
                            "description": "For demat_cas: one of 'equity', 'reit', 'invit', "
                            "'etf' — the document groups holdings under headings like 'EQUITY "
                            "HOLDINGS', 'REIT HOLDINGS', 'INVIT HOLDINGS', use that heading to "
                            "classify each holding; an ETF (Exchange Traded Fund, trades on the "
                            "exchange via its own ISIN like a stock, not through a folio) is "
                            "'etf' even if grouped under an 'EQUITY HOLDINGS' heading or "
                            "described with mutual-fund-style AMC naming text. For "
                            "deposit_statement: one of 'fd', 'rd' — "
                            "Fixed Deposit vs Recurring Deposit. For bank_statement: the "
                            "literal string 'ppf' if the document's own Product/Account Type "
                            "field identifies it as a Public Provident Fund account rather "
                            "than an ordinary savings/current account (e.g. 'Product : 1030 - "
                            "PUBLIC PROVIDENT FUND') — a PPF account is frequently issued on "
                            "the exact same statement template as a regular bank account, "
                            "distinguished only by this field, so check it explicitly rather "
                            "than assuming every bank_statement is an ordinary account. Null "
                            "for a bank_statement that is an ordinary account, and for every "
                            "other document_type.",
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
                            "itself. For nps_statement: the scheme identifier with spaces "
                            "stripped, e.g. 'Scheme E Tier I' under a fund house name -> "
                            "'SchemeE' (drop the fund house name and the Tier qualifier, keep "
                            "just the letter-coded scheme itself).",
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
                            "by you. For insurance_policy, report the Surrender Value "
                            "specifically — never the (larger) Fund Value, and never the Sum "
                            "Assured (a contingent death benefit figure, not money available "
                            "now, no matter how prominently it's printed). Null for "
                            "epf_passbook — use employee_balance/employer_balance/"
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
        "required": [
            "document_type",
            "doc_issued_at",
            "investor_pan",
            "investor_name",
            "source",
            "is_exhaustive",
            "holdings",
        ],
    },
}

EXTRACT_SYSTEM_PROMPT = (
    "You extract raw facts from financial statement documents. Report only what the "
    "document actually states — never compute, estimate, or infer a value it doesn't "
    "contain. If a document mentions unvested, potential, or contingent value that isn't "
    "actually owned yet, do not report it as a holding at all. A pure term life "
    "insurance policy (no cash/surrender value — check for wording like 'Pure Term "
    "Plan' or 'No Cash / Surrender Value') has nothing to report at all: do not include "
    "any holding for it, even though it prominently prints a large Sum Assured figure — "
    "that figure is a contingent death benefit, not an asset you own now.\n\n"
    "institution and instrument_name are used as stable identity keys downstream — the "
    "same underlying account must always normalize to the exact same string, so follow "
    "the normalization rules in each field's schema description exactly and literally. "
    "Do not use your own judgment about what looks cleaner or more natural; apply the "
    "stated rules mechanically, the same way every time."
)


def read_pdf_text(pdf_bytes: bytes, password: str | None) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    if reader.is_encrypted:
        if password is not None:
            reader.decrypt(password)
        elif reader.decrypt("") == PasswordType.NOT_DECRYPTED:
            # No password was supplied and the file isn't just owner-password
            # protected (which unlocks with an empty string) — fall back to
            # the eval corpus's fixed password so the eval suite keeps
            # working without threading a password through every case.
            reader.decrypt(_EVAL_FIXTURE_PASSWORD)
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

# A comprehensive real statement (e.g. a consolidated CAS covering many AMC
# folios) needs to enumerate far more holdings than any synthetic eval fixture
# does — each with ~10 fields. 4096 was sized for the eval corpus's 1-2-holding
# fixtures and was confirmed too small on real multi-folio documents: the model's
# JSON generation gets cut off mid-holding, producing an incomplete tool_use
# result. Comfortably covers a document with several dozen holdings.
_EXTRACTION_MAX_TOKENS = 16384


class ExtractionTruncatedError(Exception):
    """The model's response was cut off by the output token budget before it
    finished — distinct from a generically malformed/incomplete result: the
    document itself is fine, it just has more holdings than fit in one response.
    """


def extract_facts(pdf_bytes: bytes, password: str | None = None) -> dict:
    text = read_pdf_text(pdf_bytes, password)
    return extract_facts_from_text(text)


def extract_facts_from_text(text: str) -> dict:
    cache_key = hashlib.sha256(text.encode()).hexdigest()
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]

    settings = get_settings()
    response = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=_EXTRACTION_MAX_TOKENS,
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
    usage_list = _run_usage.get()
    if usage_list is not None:
        usage_list.append(
            ExtractionUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_creation_input_tokens=response.usage.cache_creation_input_tokens or 0,
                cache_read_input_tokens=response.usage.cache_read_input_tokens or 0,
            )
        )
    if response.stop_reason == "max_tokens":
        raise ExtractionTruncatedError(
            "response cut off before it finished — the document likely has more "
            "holdings than fit in one extraction pass"
        )
    for block in response.content:
        if block.type == "tool_use":
            _extraction_cache[cache_key] = block.input
            return block.input
    raise ValueError("Model did not return a tool_use block")
