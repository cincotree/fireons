from decimal import Decimal
from pathlib import Path

from ingestion.extract import extract_facts
from ingestion.model import NetWorth, Position


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


def _account_name(
    document_type: str, institution: str, identifier: str, instrument_name: str | None
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
        return f"Assets:Bank:{institution}:{identifier}"
    if document_type == "mutual_fund_cas":
        return f"Assets:Investment:MutualFund:{institution}:{identifier}:{instrument_name}"
    raise ValueError(f"unsupported document_type: {document_type}")


def ingest(current: NetWorth, files: list[Path], password: str | None = None) -> NetWorth:
    """First-pass scaffold, scoped to prove the extraction plumbing end to end against
    the `fresh` case only. Deliberately does NOT yet implement: staleness/supersession
    (as_of, doc_issued_at tie-break), completeness-driven redemption, partial-document
    safety, cross-document dedup, currency exclusion from total, identity-mismatch
    rejection, or the "Page 1 of N" truncation check. Extraction is LLM-based (see
    ingestion/extract.py), not per-institution parser code (statements/parsers/ is a
    separate, older pipeline — this one is deliberately not that).

    password, when given, is used to decrypt every file in this call — fine for a
    single-file caller (e.g. the ingestion-test upload endpoint), not yet a real
    per-file password model. When omitted (the eval harness never passes it), falls
    back to the eval fixture password, preserving existing harness behavior exactly.
    """
    positions = dict(current.positions)
    for file in files:
        facts = extract_facts(file.read_bytes(), password)
        for holding in facts["holdings"]:
            if facts["document_type"] == "epf_passbook":
                # EPF (Employee + Employer) and EPS (Pension) are tracked as separate
                # positions — EPS is a formula-based pension entitlement, not a bankable
                # lump sum like the PF corpus. The document never states a combined
                # Employee+Employer figure, so that sum happens here in code, not by
                # asking the LLM to compute it.
                epf_name = f"Assets:Retirement:EPF:{holding['identifier']}"
                eps_name = f"Assets:Retirement:EPS:{holding['identifier']}"
                epf_value = Decimal(_clean_numeric(holding["employee_balance"])) + Decimal(
                    _clean_numeric(holding["employer_balance"])
                )
                positions[epf_name] = Position(
                    account_name=epf_name,
                    value=str(epf_value),
                    currency=holding["currency"],
                    as_of=holding["as_of"],
                )
                positions[eps_name] = Position(
                    account_name=eps_name,
                    value=_clean_numeric(holding["pension_balance"]),
                    currency=holding["currency"],
                    as_of=holding["as_of"],
                )
                continue

            account_name = _account_name(
                facts["document_type"],
                holding["institution"],
                holding["identifier"],
                holding.get("instrument_name"),
            )
            positions[account_name] = Position(
                account_name=account_name,
                value=_clean_numeric(holding["value"]),
                currency=holding["currency"],
                as_of=holding["as_of"],
                units=_clean_numeric(holding.get("units")),
                nav=_clean_numeric(holding.get("nav")),
            )

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
    )
