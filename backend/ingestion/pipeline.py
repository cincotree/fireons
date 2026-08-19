from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pypdf.errors import FileNotDecryptedError, PdfReadError

from ingestion.config import get_settings
from ingestion.extract import (
    ExtractionTruncatedError,
    begin_usage_tracking,
    end_usage_tracking,
    estimate_cost_usd,
)
from ingestion.model import LLMUsage, NetWorth, Position
from ingestion.router import route_extract

_REQUIRED_FACT_KEYS = {
    "document_type",
    "doc_issued_at",
    "investor_name",
    "source",
    "is_exhaustive",
    "holdings",
}


def _clean_numeric(value: str | None) -> str | None:
    """Defensive normalization for LLM-extracted numeric strings — strips thousands
    separators and whitespace regardless of what the prompt asked for. The schema
    tells the model not to include them, but a real EPFO passbook prints Indian-style
    digit grouping ('2,29,892'), and a prompt-only guarantee isn't a guarantee: this
    is the code-side backstop so a future prompt tweak can't reintroduce
    `decimal.InvalidOperation: ConversionSyntax` crashes on real documents.
    """
    if value is None:
        return None
    return value.replace(",", "").strip()


_DEMAT_PREFIXES = {"equity": "Equity:India", "reit": "REIT", "invit": "InvIT", "etf": "ETF"}
_DEPOSIT_PREFIXES = {"fd": "FD", "rd": "RD"}

# is_exhaustive only justifies deleting an unmentioned position when the document is a
# genuine consolidated statement of multiple holdings from one issuer (a CAMS/CDSL CAS,
# an EPF passbook, an NPS statement, a bank statement). A single-instrument certificate
# (a loan statement, an SGB confirmation, one insurance policy) is trivially "exhaustive"
# of itself, but that says nothing about the customer's other unrelated holdings from the
# same source — confirmed by insurance_classification: a term-insurance statement and a
# ULIP statement share no aggregator, so both get source=None and would otherwise collide
# in the same redemption scope, with the term document's silence about the ULIP folio
# wrongly read as the ULIP being redeemed.
_EXHAUSTIVE_ELIGIBLE_TYPES = {
    "mutual_fund_cas",
    "demat_cas",
    "epf_passbook",
    "nps_statement",
    "bank_statement",
}


def _join(*parts: str | None) -> str:
    """Joins non-empty key segments with ':' — institution is the only segment
    ever omitted (when a document doesn't state it, e.g. FD_Account.pdf's
    real-world 'Fixed Deposit Summary' format, which never prints a bank name at
    all). identifier/instrument_type/instrument_name stay hard-required by their
    callers; this just keeps the key from ever containing a literal 'None'.
    """
    return ":".join(part for part in parts if part)


def _account_name(
    document_type: str,
    institution: str | None,
    identifier: str,
    instrument_name: str | None,
    instrument_type: str | None = None,
) -> str:
    """Built deterministically from stable extracted identifiers — never generated as
    free text by the LLM. Confirmed against real documents: a CAMS CAS and a CDSL CAS
    describing the identical mutual fund folio had an identical Folio Number in both,
    but differently phrased scheme-name text. If account_name were built from that free
    text, the same real holding would get two different keys depending on which
    document it came from, and cross-document dedup (see core.yaml tags: idempotency,
    mixed_sources) would be at risk of silently double-counting — the eval harness
    compares account_name as an exact key on purpose, it does not tolerate key drift
    the way it tolerates numeric noise.

    institution is a soft field: when a document genuinely doesn't state one (real,
    confirmed case: a "Fixed Deposit Summary" export with no bank name in its text,
    only an account number), the key omits that segment rather than blocking
    ingestion on it — the user can rename the account once created. A known,
    accepted trade-off: two different unidentified institutions whose identifier
    strings happen to collide would land in the same account, which is judged
    unlikely enough (real account numbers are institution-issued and long) to not
    block on.
    """
    if document_type == "bank_statement":
        if instrument_type == "ppf":
            return _join("Assets", "Retirement", "PPF", institution, identifier)
        return _join("Assets", "Bank", institution, identifier)
    if document_type == "nps_statement":
        return f"Assets:Retirement:NPS:{identifier}:{instrument_name}"
    if document_type == "mutual_fund_cas":
        return _join("Assets", "Investment", "MutualFund", institution, identifier, instrument_name)
    if document_type == "loan_statement":
        return _join("Liabilities", "Loan", institution, identifier)
    if document_type == "brokerage_statement":
        return f"Assets:Investment:Equity:US:{identifier}"
    if document_type == "demat_cas":
        # instrument_name (the security's name, e.g. "Avenue Supermarts
        # Limited") is a soft field here — same idiom as institution above —
        # appended for a readable leaf label instead of a bare ISIN. The ISIN
        # segment stays regardless, since that's what actually guarantees the
        # key is stable and collision-safe.
        return _join("Assets", "Investment", _DEMAT_PREFIXES[instrument_type], identifier, instrument_name)
    if document_type == "sgb_confirmation":
        return f"Assets:Investment:SGB:{identifier}"
    if document_type == "deposit_statement":
        return _join("Assets", "Deposit", _DEPOSIT_PREFIXES[instrument_type], institution, identifier)
    if document_type == "insurance_policy":
        return _join("Assets", "Insurance", "ULIP", institution, identifier)
    raise ValueError(f"unsupported document_type: {document_type}")


def _should_replace(existing: Position | None, new: Position) -> bool:
    """The (as_of, doc_issued_at) supersession rule: newer as_of always wins; on a tie
    (a same-day correction, see the restatement eval case), newer doc_issued_at wins,
    regardless of which document was uploaded/processed first. No existing position ->
    always write. Applied uniformly whether "existing" came from the caller's seeded
    NetWorth or from an earlier file processed in this same ingest() call, so upload
    order never matters — confirmed via the eval suite that a naive "last file
    processed wins" implementation gives a different (wrong) answer depending on file
    order; this rule is what makes the answer order-independent instead.
    """
    if existing is None:
        return True
    if new.as_of != existing.as_of:
        return new.as_of > existing.as_of
    if existing.doc_issued_at is None:
        return new.doc_issued_at is not None
    if new.doc_issued_at is None:
        return False
    return new.doc_issued_at > existing.doc_issued_at


def _document_supersedes(existing: Position, doc_issued_at: datetime) -> bool:
    """Whether an exhaustive document's silence about `existing` should be read as
    redemption — only if the document is at least as current as what's already known.
    A stale exhaustive document's silence isn't informative (see
    stale_exhaustive_does_not_zero): it can't tell you something was redeemed after the
    document was even generated. Falls back to as_of (midnight) when existing has no
    doc_issued_at recorded, e.g. seeded/caller-provided state.
    """
    reference = existing.doc_issued_at
    if reference is None:
        reference = datetime.combine(existing.as_of, datetime.min.time())
    return doc_issued_at >= reference


def ingest(
    current: NetWorth,
    files: list[Path],
    password: str | None = None,
    passwords: dict[str, str] | None = None,
) -> NetWorth:
    """Scoped so far to: extraction across bank/mutual-fund/EPF/loan/brokerage/demat/
    SGB/deposit/NPS/insurance documents, (as_of, doc_issued_at) staleness/
    supersession, source-scoped completeness/redemption, and a safety pair: a
    document that isn't actually a statement gets classified 'unrecognized' rather
    than force-fit into the nearest category; a malformed/unreadable PDF is
    quarantined rather than crashing the whole call. Deliberately does NOT yet
    implement: the "Page 1 of N" truncation check. A deterministic parser tier
    (see ingestion/parsers/) is tried first; anything it doesn't recognize
    falls back to LLM-based extraction (see ingestion/extract.py).

    There is deliberately no identity verification between documents or against a
    user profile — this is a single-tenant, self-hosted tool, so there's no one to
    protect the uploader from except themselves.

    password is the batch-wide fallback used to decrypt any file without its own
    entry in `passwords`. When omitted (the eval harness never passes it), falls
    back to the eval fixture password, preserving existing harness behavior exactly.

    passwords, when given, maps a file's `.name` to the password for that specific
    file — real uploads commonly mix statements from different institutions, each
    with its own password. A file's own entry (if present) always wins over the
    batch-wide `password`.
    """
    usage_token = begin_usage_tracking()
    positions = dict(current.positions)
    warnings = list(current.warnings)

    for file in files:
        file_password = passwords.get(file.name, password) if passwords else password
        try:
            facts = route_extract(file.read_bytes(), file_password)
        except FileNotDecryptedError:
            warnings.append(f"quarantined {file.name} — wrong or missing password")
            continue
        except PdfReadError:
            warnings.append(f"quarantined {file.name} — not a valid PDF")
            continue
        except ExtractionTruncatedError:
            warnings.append(
                f"quarantined {file.name} — too many holdings to extract in one "
                f"pass, the file itself is fine"
            )
            continue

        # The LLM's tool-use schema marks these fields "required", but that's a
        # prompt-level request, not an enforced guarantee — an occasional malformed
        # response can still omit one entirely (confirmed happening in practice).
        # Quarantine that one file rather than let a raw KeyError crash the whole
        # batch, same safety posture as every other quarantine case here.
        if not _REQUIRED_FACT_KEYS.issubset(facts):
            warnings.append(f"quarantined {file.name} — extraction returned an incomplete result")
            continue

        if facts["document_type"] == "unrecognized":
            warnings.append(f"could not classify {file.name} as a known statement type")
            continue

        # The key can be present but still null — the schema documents that as
        # valid only for 'unrecognized' documents (already handled above), but
        # nothing enforces the model actually honoring that for every other type.
        # A malformed value is exactly as unusable as a missing key.
        if not isinstance(facts.get("doc_issued_at"), str):
            warnings.append(f"quarantined {file.name} — extraction returned an incomplete result")
            continue

        # Only parser-produced facts carry this key — a parser may return a complete
        # holding with a soft field missing (e.g. no account-holder name found) rather
        # than deferring the whole file to the LLM; that gets surfaced here rather
        # than silently dropped. The LLM path never sets this key, so it's a no-op
        # for LLM-sourced facts.
        warnings.extend(f"{file.name}: {w}" for w in facts.get("warnings", []))

        doc_issued_at = datetime.fromisoformat(facts["doc_issued_at"])
        source = facts["source"]
        mentioned: set[str] = set()

        for holding in facts["holdings"]:
            if facts["document_type"] == "epf_passbook":
                # EPF (Employee + Employer) and EPS (Pension) are tracked as separate
                # positions — EPS is a formula-based pension entitlement, not a bankable
                # lump sum like the PF corpus. The document never states a combined
                # Employee+Employer figure, so that sum happens here in code, not by
                # asking the LLM to compute it.
                epf_name = f"Assets:Retirement:EPF:{holding['identifier']}"
                eps_name = f"Assets:Retirement:EPS:{holding['identifier']}"
                mentioned.update((epf_name, eps_name))
                epf_value = Decimal(_clean_numeric(holding.get("employee_balance"))) + Decimal(
                    _clean_numeric(holding.get("employer_balance"))
                )
                new_epf = Position(
                    account_name=epf_name,
                    value=str(epf_value),
                    currency=holding["currency"],
                    as_of=holding["as_of"],
                    doc_issued_at=doc_issued_at,
                    source=source,
                )
                if _should_replace(positions.get(epf_name), new_epf):
                    positions[epf_name] = new_epf
                new_eps = Position(
                    account_name=eps_name,
                    value=_clean_numeric(holding.get("pension_balance")),
                    currency=holding["currency"],
                    as_of=holding["as_of"],
                    doc_issued_at=doc_issued_at,
                    source=source,
                )
                if _should_replace(positions.get(eps_name), new_eps):
                    positions[eps_name] = new_eps
                continue

            account_name = _account_name(
                facts["document_type"],
                holding.get("institution"),
                holding["identifier"],
                holding.get("instrument_name"),
                holding.get("instrument_type"),
            )
            mentioned.add(account_name)
            value = _clean_numeric(holding.get("value"))
            if facts["document_type"] == "loan_statement":
                # The model reports Outstanding Principal as printed (positive) — the
                # negative sign that makes a liability actually subtract from net worth
                # is applied here in code, never by the LLM.
                value = str(-Decimal(value))
            new_position = Position(
                account_name=account_name,
                value=value,
                currency=holding["currency"],
                as_of=holding["as_of"],
                units=_clean_numeric(holding.get("units")),
                nav=_clean_numeric(holding.get("nav")),
                doc_issued_at=doc_issued_at,
                source=source,
            )
            if _should_replace(positions.get(account_name), new_position):
                positions[account_name] = new_position

        if facts["is_exhaustive"] and facts["document_type"] in _EXHAUSTIVE_ELIGIBLE_TYPES:
            for key, existing in list(positions.items()):
                if key in mentioned:
                    continue
                if existing.source != source:
                    continue
                if _document_supersedes(existing, doc_issued_at):
                    del positions[key]

    total = sum(
        (
            Decimal(p.value)
            for p in positions.values()
            if p.currency == current.reporting_currency
        ),
        start=Decimal("0"),
    )
    as_of = max((p.as_of for p in positions.values()), default=None)

    usage = end_usage_tracking(usage_token)
    llm_usage = LLMUsage(
        call_count=len(usage),
        input_tokens=sum(u.input_tokens for u in usage),
        output_tokens=sum(u.output_tokens for u in usage),
        cache_creation_input_tokens=sum(u.cache_creation_input_tokens for u in usage),
        cache_read_input_tokens=sum(u.cache_read_input_tokens for u in usage),
        estimated_cost_usd=estimate_cost_usd(usage, get_settings().anthropic_model),
    )

    return NetWorth(
        as_of=as_of,
        reporting_currency=current.reporting_currency,
        positions=positions,
        total=str(total),
        warnings=warnings,
        llm_usage=llm_usage,
    )
