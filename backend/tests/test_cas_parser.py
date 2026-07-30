from decimal import Decimal

import pytest

from statements.parsers.cas import CASParser
from statements.parsers.exceptions import IncorrectPasswordError, UnrecognizedStatementFormatError
from tests.fixtures.generate_cas_fixture import FIXTURES_DIR, TEST_CAS_PDF_PASSWORD


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


@pytest.fixture
def parser() -> CASParser:
    return CASParser()


class TestCASParser:
    def test_multi_amc_folio_scheme_happy_path(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)

        assert result.statement_date.isoformat() == "2025-03-31"
        assert result.warnings == []
        assert len(result.holdings) == 4

        by_folio = {h.folio_number: h for h in result.holdings}

        aditya = by_folio["1234567"]
        assert aditya.amc == "Aditya Birla Sun Life"
        assert aditya.scheme_name == "T001 - Test Bluechip Fund - Growth-Direct Plan (Non-Demat)"
        assert aditya.isin == "INF999A01111"
        assert aditya.units == Decimal("1234.567")
        assert aditya.nav == Decimal("45.6789")
        assert aditya.market_value == Decimal("56391.23")
        assert aditya.source == "CAMS"

        sbi = by_folio["9988776"]
        assert sbi.amc == "SBI"
        assert sbi.market_value == Decimal("125061.70")

    def test_zero_balance_scheme_still_parsed(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)
        redeemed = next(h for h in result.holdings if h.folio_number == "7654321/0")
        assert redeemed.amc == "HDFC"
        assert redeemed.units == Decimal("0.000")
        assert redeemed.market_value == Decimal("0.00")
        assert redeemed.source == "KFINTECH"

    def test_scheme_wrapping_across_multiple_lines(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)
        sbi = next(h for h in result.holdings if h.folio_number == "9988776")
        assert sbi.scheme_name == "T003 - Test Small Cap Fund - Regular Plan - Growth (Demat)"

    def test_unknown_amc_falls_back_to_guess_with_warning(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)
        zephyr = next(h for h in result.holdings if h.folio_number == "5551111")
        assert zephyr.amc == "Zephyr Capital"
        assert len(zephyr.warnings) == 1
        assert "Zephyr Capital" in zephyr.warnings[0]

    def test_dangling_incomplete_scheme_is_skipped_with_warning(self, parser: CASParser):
        result = parser.parse(
            _fixture_bytes("cas_with_unparseable_scheme.pdf"), TEST_CAS_PDF_PASSWORD
        )
        assert len(result.holdings) == 4
        assert len(result.warnings) == 1
        assert "9999999" in result.warnings[0]
        assert not any(h.folio_number == "9999999" for h in result.holdings)

    def test_wrong_password_raises(self, parser: CASParser):
        with pytest.raises(IncorrectPasswordError):
            parser.parse(_fixture_bytes("cas_valid.pdf"), "wrong-password")

    def test_no_recognizable_holdings_raises(self, parser: CASParser):
        with pytest.raises(UnrecognizedStatementFormatError):
            parser.parse(_fixture_bytes("cas_no_holdings.pdf"), TEST_CAS_PDF_PASSWORD)

    def test_reupload_fixtures_share_folio_and_scheme_but_differ_in_value(
        self, parser: CASParser
    ):
        before = parser.parse(_fixture_bytes("cas_reupload_before.pdf"), TEST_CAS_PDF_PASSWORD)
        after = parser.parse(_fixture_bytes("cas_reupload_after.pdf"), TEST_CAS_PDF_PASSWORD)

        assert before.holdings[0].folio_number == after.holdings[0].folio_number
        assert before.holdings[0].scheme_name == after.holdings[0].scheme_name
        assert before.holdings[0].market_value != after.holdings[0].market_value
        assert before.statement_date != after.statement_date
