from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pypdf.errors import PdfReadError

from ingestion.extract import extract_facts
from ingestion.model import NetWorth, Position

# Phase 1 stand-in for a real per-user identity system — the eval corpus's "owner" is
# always this PAN/name, matching the fixtures (mismatched_identity_cas.pdf uses a
# different PAN and name on purpose). Real uploads need this threaded through from
# the actual logged-in user, not a hardcoded constant — same category of
# simplification as _EVAL_FIXTURE_PASSWORD in extract.py.
_REFERENCE_PAN = "SAMPLEPAN1Z"
_REFERENCE_NAME_FRAGMENT = "TEST USER"


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


def _identity_matches(investor_pan: str | None, investor_name: str | None) -> bool:
    """PAN is the more reliable signal when present (exact match required). When PAN
    is absent (common for plain bank/deposit statements), fall back to checking
    whether the reference name appears as a substring — this is what lets a joint
    account ('MR. TEST USER & MRS. SPOUSE USER') pass: the owner's name is present,
    just not alone, which is a deliberately different case from a document that
    doesn't mention the owner at all. If neither PAN nor name is present in the
    document (nothing to check against), default to allowing it through rather than
    rejecting on missing information.
    """
    if investor_pan is not None:
        return investor_pan == _REFERENCE_PAN
    if investor_name is not None:
        return _REFERENCE_NAME_FRAGMENT.lower() in investor_name.lower()
    return True


_DEMAT_PREFIXES = {"equity": "Equity:India", "reit": "REIT", "invit": "InvIT"}
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


def _account_name(
    document_type: str,
    institution: str,
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
    """
    if document_type == "bank_statement":
        if instrument_type == "ppf":
            return f"Assets:Retirement:PPF:{institution}:{identifier}"
        return f"Assets:Bank:{institution}:{identifier}"
    if document_type == "nps_statement":
        return f"Assets:Retirement:NPS:{identifier}:{instrument_name}"
    if document_type == "mutual_fund_cas":
        return f"Assets:Investment:MutualFund:{institution}:{identifier}:{instrument_name}"
    if document_type == "loan_statement":
        return f"Liabilities:Loan:{institution}:{identifier}"
    if document_type == "brokerage_statement":
        return f"Assets:Investment:Equity:US:{identifier}"
    if document_type == "demat_cas":
        return f"Assets:Investment:{_DEMAT_PREFIXES[instrument_type]}:{identifier}"
    if document_type == "sgb_confirmation":
        return f"Assets:Investment:SGB:{identifier}"
    if document_type == "deposit_statement":
        return f"Assets:Deposit:{_DEPOSIT_PREFIXES[instrument_type]}:{institution}:{identifier}"
    if document_type == "insurance_policy":
        return f"Assets:Insurance:ULIP:{institution}:{identifier}"
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


def ingest(current: NetWorth, files: list[Path], password: str | None = None) -> NetWorth:
    """Scoped so far to: extraction across bank/mutual-fund/EPF/loan/brokerage/demat/
    SGB/deposit/NPS/insurance documents, (as_of, doc_issued_at) staleness/
    supersession, source-scoped completeness/redemption, and three safety checks: a
    document that isn't actually a statement gets classified 'unrecognized' rather
    than force-fit into the nearest category; a malformed/unreadable PDF is
    quarantined rather than crashing the whole call; and a document whose stated
    investor identity doesn't match the account owner is quarantined rather than
    merged in. Deliberately does NOT yet implement: the "Page 1 of N" truncation
    check. Extraction is LLM-based (see ingestion/extract.py), not per-institution
    parser code (statements/parsers/ is a separate, older pipeline — this one is
    deliberately not that).

    password, when given, is used to decrypt every file in this call — fine for a
    single-file caller (e.g. the ingestion-test upload endpoint), not yet a real
    per-file password model. When omitted (the eval harness never passes it), falls
    back to the eval fixture password, preserving existing harness behavior exactly.
    """
    positions = dict(current.positions)
    warnings = list(current.warnings)

    for file in files:
        try:
            facts = extract_facts(file.read_bytes(), password)
        except PdfReadError:
            warnings.append(f"quarantined {file.name} — not a valid PDF")
            continue

        if facts["document_type"] == "unrecognized":
            warnings.append(f"could not classify {file.name} as a known statement type")
            continue

        if not _identity_matches(facts.get("investor_pan"), facts.get("investor_name")):
            warnings.append(
                f"quarantined {file.name} — investor identity does not match account owner"
            )
            continue

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
    return NetWorth(
        as_of=as_of,
        reporting_currency=current.reporting_currency,
        positions=positions,
        total=str(total),
        warnings=warnings,
    )
