# Statement Ingestion Pipeline

`ingest(current_nw, files) -> new_nw` — turns a batch of uploaded financial
statement PDFs into a `NetWorth` ledger state. Extraction is routed
(`router.route_extract`): a deterministic parser (`parsers/`) handles a document if
one recognizes its format, otherwise it falls back to the LLM (`extract.py`). This
is a standalone pipeline (Phase 1): it does not write to the app's real
`Account`/`Balance` database tables, and it is not wired into the real net-worth
dashboard yet — that's separate, later work.

## What's implemented

### Document types

The extractor (`extract.py`) recognizes 11 document types, driven by a single
tool-use schema rather than per-institution code:

| Type | Covers |
|---|---|
| `bank_statement` | Regular accounts, PPF accounts, joint accounts |
| `mutual_fund_cas` | CAMS and CDSL consolidated account statements |
| `epf_passbook` | EPF + EPS tracked as separate positions (see below) |
| `loan_statement` | Outstanding principal, reported as a negative position |
| `brokerage_statement` | International (e.g. US) single-stock holdings |
| `demat_cas` | NSDL/CDSL — equity, REIT, and InvIT holdings |
| `sgb_confirmation` | Sovereign Gold Bond purchase confirmations |
| `deposit_statement` | Fixed and recurring deposits |
| `nps_statement` | National Pension System, per-scheme |
| `insurance_policy` | ULIP/endowment (surrender value) vs. term (excluded) |
| `unrecognized` | Anything that isn't actually a statement |

Nothing in the schema is hardcoded to a specific institution — `institution` is
extracted via a general normalization rule ("strip legal-entity suffixes, prefer
the short brand name"), not a lookup table. A statement from an institution never
seen in the eval fixtures is expected to work the same way a new one does; it just
hasn't been proven against a fixture yet (see "What's not covered" below).

### Design decisions

- **Deterministic account keys.** Keys like `Assets:Bank:HDFC:6789` are always
  built in code (`pipeline._account_name`) from stable extracted identifiers
  (folio number, ISIN, account number) — never generated as free text by the LLM.
  This is what makes cross-document dedup reliable: a CAMS CAS and a CDSL CAS
  describing the same fund folio have differently-worded scheme names but an
  identical Folio Number, and the key is built from the identifier, not the name.

- **Staleness/supersession.** `(as_of, doc_issued_at)` ordering — a newer `as_of`
  always wins; on a tie (a same-day correction), the document that was actually
  *issued* later wins, independent of upload order. Proven order-independent via
  the eval harness's permutation sweep, not assumed.

- **Source-scoped completeness/redemption.** An exhaustive statement's silence
  about a position it would have mentioned means that position is gone — but only
  within the same `source` (a CDSL statement's completeness says nothing about
  CAMS-sourced holdings — confirmed against real evidence that CDSL genuinely
  covers more funds than CAMS) and only for document types that are genuine
  consolidated statements (`mutual_fund_cas`, `demat_cas`, `epf_passbook`,
  `nps_statement`, `bank_statement`). A single-instrument certificate (a term
  insurance policy, an SGB confirmation, a loan statement) is trivially
  "exhaustive" of itself but says nothing about other holdings from the same
  source — this restriction exists because a term-insurance and a ULIP statement
  from the same insurer, with no aggregator between them, would otherwise collide
  in the same redemption scope and the term policy's silence about the ULIP folio
  would wrongly zero it out.

- **Safety pair.** A non-statement document is classified `unrecognized` rather
  than force-fit into the nearest category. A malformed/unreadable PDF is
  quarantined (`PdfReadError`, caught before any LLM call — free) rather than
  crashing the whole batch. There is deliberately no identity verification
  between documents or against a user profile — this is a single-tenant,
  self-hosted tool, so there's no one to protect the uploader from except
  themselves.

- **EPF split.** A passbook reports Employee + Employer balance and a separate
  Pension (EPS) balance; these become two positions (`Assets:Retirement:EPF:...`
  and `Assets:Retirement:EPS:...`), summed in code, never by the LLM.

- **Deterministic parser tier.** `router.route_extract()` tries every parser in
  `parsers/` (one module per related document-type group — bank accounts, loans,
  deposits, mutual funds, demat, retirement, SGB, insurance, brokerage) before ever
  calling the LLM. Each `try_parse_X(text) -> dict | None` either returns a
  complete, correct facts dict or defers — it never guesses or returns a value it
  isn't confident in. A parser may return a holding with a *soft* field missing
  (e.g. no account-holder name, or no confirmed institution — real example:
  `FD_Account.pdf`'s "Fixed Deposit Summary" export, which never prints a bank
  name at all) plus a warning rather than deferring the whole file. Only
  `identifier`/`instrument_type`/`instrument_name` (the fields
  `pipeline._account_name()` needs to build a stable, collision-safe key,
  depending on document type) and what `ingest()` reads unconditionally
  (`doc_issued_at`) are hard-required — `institution` is soft everywhere; when
  absent, `_account_name()` just omits that segment from the key rather than
  deferring the whole file to the LLM. This is what makes cost and correctness both improve
  together for a known format, instead of trading one for the other: proven
  zero-LLM-call on the full 13-file `composite_real_world_portfolio` case (was 13
  live calls), with the entire 159-invocation eval suite passing identically
  either way. Parsers are only as trustworthy as the fixtures they were built
  against — see "What's not covered yet" below.

- **Cost controls.** The parser tier above is the primary one. For whatever still
  reaches the LLM: an in-process cache (keyed by document text hash) avoids
  re-extracting the same file twice within one `ingest()` call, plus Anthropic
  prompt caching on the (large, static) tool schema and system prompt.

- **Rate limiting** (`rate_limit.py`, enforced at the API layer, not inside
  `ingest()` itself) — 50MB cumulative upload volume per user per hour is the
  binding guard, since cost tracks bytes sent to the LLM, not request count; a
  40/hour request-count check is just a loose backstop against a runaway loop of
  tiny files.

### Self-verifying invariants (`invariants.py`)

Label-free correctness checks, independent of extraction: units × NAV ≈ value,
positions sum to the stated total (currency-aware), no `as_of` date in the future,
every account key starts with `Assets:`/`Liabilities:` and matches its own
`account_name`.

## What's not covered yet

- **Persistence.** `ingest()` is a pure function; nothing writes to the real
  `Account`/`Balance` tables.
- **Truncation detection.** A partial/truncated upload (e.g. only page 1 of a
  multi-page statement) isn't caught.
- **Non-Indian institutions are architecturally supported but not yet proven** —
  no fixture/eval case exists for e.g. a UK or EU bank statement. The design
  should generalize (see "Document types" above), but this project's whole
  methodology is proving behavior via eval cases rather than assuming it from
  architecture, so treat it as untested until a fixture backs it up.
- **Parsers are tested against synthetic, unvalidated fixtures.** Every fixture in
  `tests/evals/fixtures/generate_eval_fixtures.py` except HDFC's (which has a
  separately real-document-validated generator, `tests/fixtures/generate_hdfc_fixture.py`)
  is explicitly marked "NOT confirmed against a real statement — a plausible
  approximation" in that module's own docstring. A parser passing the eval suite
  proves it's internally consistent with that approximation, not that it matches a
  real CAMS/CDSL/EPFO/NPS/insurer/brokerage document layout. Spot-check the
  highest-value parsers against real reference documents before trusting the cost
  savings in production.

## Eval suite

31 cases in `tests/evals/cases/core.yaml`, run against synthetic fixtures only
(`tests/evals/fixtures/`, generated via `generate_eval_fixtures.py` — no real
financial documents are ever committed). Full details, including how to run a
specific case without triggering the whole (costly, live-API) suite:
see `tests/evals/harness.py` and `tests/evals/test_ledger_properties.py`.
