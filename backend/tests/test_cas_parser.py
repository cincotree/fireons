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

        alpha = by_folio["1122334"]
        assert alpha.amc == "Alpha Mutual Fund"
        assert alpha.scheme_name == "Alpha Bluechip Growth Fund"
        assert alpha.isin == "INF111A01234"
        assert alpha.units == Decimal("1234.567")
        assert alpha.nav == Decimal("45.6789")
        assert alpha.market_value == Decimal("56391.23")

        beta = by_folio["9988776"]
        assert beta.amc == "Beta Mutual Fund"
        assert beta.market_value == Decimal("125061.70")

    def test_zero_balance_scheme_still_parsed(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)
        redeemed = next(h for h in result.holdings if h.folio_number == "9988777")
        assert redeemed.units == Decimal("0.000")
        assert redeemed.market_value == Decimal("0.00")

    def test_missing_isin_still_parses(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_valid.pdf"), TEST_CAS_PDF_PASSWORD)
        no_isin = next(h for h in result.holdings if h.folio_number == "1122335")
        assert no_isin.isin is None
        assert no_isin.units == Decimal("500.000")

    def test_unparseable_scheme_is_skipped_with_warning(self, parser: CASParser):
        result = parser.parse(
            _fixture_bytes("cas_with_unparseable_scheme.pdf"), TEST_CAS_PDF_PASSWORD
        )
        assert len(result.holdings) == 4
        assert len(result.warnings) == 1
        assert "Gamma Unparseable Fund" in result.warnings[0]
        assert not any(h.scheme_name == "Gamma Unparseable Fund" for h in result.holdings)

    def test_wrong_password_raises(self, parser: CASParser):
        with pytest.raises(IncorrectPasswordError):
            parser.parse(_fixture_bytes("cas_valid.pdf"), "wrong-password")

    def test_no_recognizable_holdings_raises(self, parser: CASParser):
        with pytest.raises(UnrecognizedStatementFormatError):
            parser.parse(_fixture_bytes("cas_no_holdings.pdf"), TEST_CAS_PDF_PASSWORD)

    def test_combined_summary_line_variant(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_combined_variant.pdf"), TEST_CAS_PDF_PASSWORD)
        assert len(result.holdings) == 1
        assert result.holdings[0].market_value == Decimal("56391.23")

    def test_three_labeled_lines_variant(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_labeled_variant.pdf"), TEST_CAS_PDF_PASSWORD)
        assert len(result.holdings) == 1
        assert result.holdings[0].market_value == Decimal("44561.70")

    def test_columnar_variant(self, parser: CASParser):
        result = parser.parse(_fixture_bytes("cas_columnar_variant.pdf"), TEST_CAS_PDF_PASSWORD)
        assert len(result.holdings) == 1
        assert result.holdings[0].market_value == Decimal("125061.70")

    def test_reupload_fixtures_share_folio_and_scheme_but_differ_in_value(
        self, parser: CASParser
    ):
        before = parser.parse(_fixture_bytes("cas_reupload_before.pdf"), TEST_CAS_PDF_PASSWORD)
        after = parser.parse(_fixture_bytes("cas_reupload_after.pdf"), TEST_CAS_PDF_PASSWORD)

        assert before.holdings[0].folio_number == after.holdings[0].folio_number
        assert before.holdings[0].scheme_name == after.holdings[0].scheme_name
        assert before.holdings[0].market_value != after.holdings[0].market_value
        assert before.statement_date != after.statement_date
