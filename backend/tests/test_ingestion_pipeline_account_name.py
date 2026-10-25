from ingestion.pipeline import _account_name


def test_demat_cas_categories_are_kept_separate():
    """Each instrument_type maps to its own top-level category under
    Assets:Investment — an ETF must never collapse into the same category as
    an ordinary equity holding. Confirmed as a real usability bug: an ETF
    correctly captured with the right value was still effectively invisible
    to the user, buried under Equity:India among two dozen ordinary stocks
    with no way to tell them apart in the account tree."""
    equity = _account_name("demat_cas", None, "INE000A00001", "Sample Equity Limited", "equity")
    etf = _account_name("demat_cas", None, "INF000B00002", "Sample ETF Gold Bees", "etf")
    reit = _account_name("demat_cas", None, "INE000C00003", "Sample REIT Trust", "reit")
    invit = _account_name("demat_cas", None, "INE000D00004", "Sample InvIT Trust", "invit")

    assert equity == "Assets:Investment:Equity:India:INE000A00001:Sample Equity Limited"
    assert etf == "Assets:Investment:ETF:INF000B00002:Sample ETF Gold Bees"
    assert reit == "Assets:Investment:REIT:INE000C00003:Sample REIT Trust"
    assert invit == "Assets:Investment:InvIT:INE000D00004:Sample InvIT Trust"

    # No two categories can ever produce the same key for different ISINs —
    # the category segment must actually appear in each string.
    assert "Equity" in equity and "ETF" not in equity
    assert "ETF" in etf and "Equity" not in etf


def test_demat_cas_instrument_name_is_soft():
    """instrument_name (the security's display name) is optional — when a
    parser can't determine it, the account key falls back to the ISIN alone
    rather than embedding a literal 'None' in the path."""
    with_name = _account_name("demat_cas", None, "INE000A00001", "Sample Equity Limited", "equity")
    without_name = _account_name("demat_cas", None, "INE000A00001", None, "equity")

    assert with_name == "Assets:Investment:Equity:India:INE000A00001:Sample Equity Limited"
    assert without_name == "Assets:Investment:Equity:India:INE000A00001"
    assert "None" not in without_name


def test_bank_statement_and_deposit_statement_institution_is_soft():
    """institution is optional for every document type that uses it — when a
    document genuinely doesn't state one (real, confirmed case: FD_Account.pdf's
    'Fixed Deposit Summary' export, no bank name anywhere in its text), the
    key omits that segment instead of blocking ingestion on it or embedding a
    literal 'None'."""
    bank_with_institution = _account_name("bank_statement", "HDFC", "6789", None, None)
    bank_without_institution = _account_name("bank_statement", None, "6789", None, None)
    assert bank_with_institution == "Assets:Bank:HDFC:6789"
    assert bank_without_institution == "Assets:Bank:6789"

    deposit_with_institution = _account_name("deposit_statement", "HDFC", "12345", None, "fd")
    deposit_without_institution = _account_name("deposit_statement", None, "12345", None, "fd")
    assert deposit_with_institution == "Assets:Deposit:FD:HDFC:12345"
    assert deposit_without_institution == "Assets:Deposit:FD:12345"
    assert "None" not in deposit_without_institution
