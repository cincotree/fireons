from ingestion.parsers.bank_accounts import try_parse_chase, try_parse_hdfc, try_parse_icici
from tests.evals.fixtures.generate_eval_fixtures import (
    CHASE_2026_07_LINES,
    CHASE_REAL_LAYOUT_2026_07_LINES,
    HDFC_2026_07_LINES,
    HDFC_JOINT_2026_07_LINES,
    HDFC_LOAN_2026_07_LINES,
    ICICI_2026_07_LINES,
    PPF_2026_07_LINES,
    UNKNOWN_DOCUMENT_LINES,
)


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_hdfc_parses_expected_facts():
    facts = try_parse_hdfc(_text(HDFC_2026_07_LINES))
    assert facts is not None
    assert facts["document_type"] == "bank_statement"
    assert facts["is_exhaustive"] is False
    assert facts["source"] == "HDFC"
    assert facts["investor_name"] == "MR. TEST USER"
    assert facts["doc_issued_at"] == "2026-07-31"
    holding = facts["holdings"][0]
    assert holding["institution"] == "HDFC"
    assert holding["identifier"] == "6789"
    assert holding["instrument_type"] is None
    assert holding["value"] == "150000.00"
    assert holding["currency"] == "INR"
    assert holding["as_of"] == "2026-07-31"


def test_hdfc_ppf_variant_sets_instrument_type():
    facts = try_parse_hdfc(_text(PPF_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["instrument_type"] == "ppf"
    assert holding["identifier"] == "8776"
    assert holding["value"] == "192600.00"


def test_hdfc_joint_account_keeps_both_names():
    facts = try_parse_hdfc(_text(HDFC_JOINT_2026_07_LINES))
    assert facts is not None
    assert facts["investor_name"] == "MR. TEST USER & MRS. SPOUSE USER"
    assert facts["holdings"][0]["identifier"] == "8877"
    assert facts["holdings"][0]["value"] == "105000.00"


def test_hdfc_defers_loan_statement_to_its_own_parser():
    assert try_parse_hdfc(_text(HDFC_LOAN_2026_07_LINES)) is None


def test_hdfc_does_not_match_unrelated_document():
    assert try_parse_hdfc(_text(UNKNOWN_DOCUMENT_LINES)) is None


def test_icici_parses_expected_facts():
    facts = try_parse_icici(_text(ICICI_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["institution"] == "ICICI"
    assert holding["identifier"] == "4321"
    assert holding["value"] == "80000.00"
    assert holding["currency"] == "INR"
    assert facts["doc_issued_at"] == "2026-07-31"
    assert facts["investor_name"] == "TEST USER"


def test_icici_does_not_match_hdfc_text():
    assert try_parse_icici(_text(HDFC_2026_07_LINES)) is None


def test_chase_parses_expected_facts_with_us_currency_and_date_order():
    facts = try_parse_chase(_text(CHASE_2026_07_LINES))
    assert facts is not None
    holding = facts["holdings"][0]
    assert holding["institution"] == "Chase"
    assert holding["identifier"] == "1234"
    assert holding["value"] == "1000.00"
    assert holding["currency"] == "USD"
    assert holding["as_of"] == "2026-07-31"
    assert facts["doc_issued_at"] == "2026-07-31"
    assert facts["investor_name"] == "TEST USER"


def test_chase_does_not_match_hdfc_text():
    assert try_parse_chase(_text(HDFC_2026_07_LINES)) is None


def test_chase_matches_real_institution_wording_case_insensitively():
    """A real Chase statement prints 'JPMorgan Chase Bank, N.A.', never the
    literal all-caps 'CHASE BANK' the original exact-match check required —
    confirmed by inspecting a real statement, where the old check silently
    deferred every genuine Chase document to the LLM regardless of whether
    the rest of its layout was otherwise parseable. Isolates the gate fix
    from the (separately real, separately unfixable) layout differences by
    reusing the synthetic fixture's otherwise-parseable Indian-statement-
    style structure with only the institution line swapped to real wording.
    """
    real_wording_text = _text(CHASE_2026_07_LINES).replace(
        "CHASE BANK", "JPMorgan Chase Bank, N.A."
    )
    facts = try_parse_chase(real_wording_text)
    assert facts is not None
    assert facts["holdings"][0]["identifier"] == "1234"


def test_chase_real_layout_defers_to_llm_not_a_parser_bug():
    """The real Chase layout (see CHASE_REAL_LAYOUT_2026_07_LINES) separates
    the account number from its 'Account Number:' label (a pypdf extraction
    artifact of Chase's multi-column layout, confirmed against a real
    statement) and uses 'Beginning/Ending Balance' wording this parser was
    never built to recognize (it only recognizes 'closing bal', matching
    Indian-bank statements). try_parse_chase() must correctly return None
    here — silently guessing at the account number's position from one
    observed sample would violate this parser tier's core contract (return a
    complete, confident result, or defer — never guess)."""
    assert try_parse_chase(_text(CHASE_REAL_LAYOUT_2026_07_LINES)) is None
