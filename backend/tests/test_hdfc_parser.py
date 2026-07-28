from decimal import Decimal

import pytest

from statements.parsers.exceptions import (
    IncorrectPasswordError,
    InvalidPDFError,
    UnrecognizedStatementFormatError,
    UnsupportedBankError,
)
from statements.parsers.hdfc import HDFCStatementParser
from statements.parsers.registry import get_parser, list_supported_banks
from tests.fixtures.generate_hdfc_fixture import FIXTURES_DIR, TEST_PDF_PASSWORD


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


class TestHDFCStatementParser:
    def test_parse_happy_path(self):
        parser = HDFCStatementParser()
        result = parser.parse(_fixture_bytes("hdfc_statement_valid.pdf"), TEST_PDF_PASSWORD)

        assert result.bank == "HDFC"
        assert result.account_holder_name == "MR. TEST USER"
        assert result.account_number == "50100123456789"
        assert result.account_number_last4 == "6789"
        assert result.currency == "INR"
        assert result.closing_balance == Decimal("128456.78")
        assert result.statement_date.isoformat() == "2025-03-31"
        assert result.warnings == []

    def test_parse_wrong_password(self):
        parser = HDFCStatementParser()
        with pytest.raises(IncorrectPasswordError):
            parser.parse(_fixture_bytes("hdfc_statement_valid.pdf"), "wrong-password")

    def test_parse_corrupted_or_non_pdf_file(self):
        parser = HDFCStatementParser()
        with pytest.raises(InvalidPDFError):
            parser.parse(_fixture_bytes("not_a_pdf.txt"), TEST_PDF_PASSWORD)

    def test_parse_unrecognized_layout(self):
        parser = HDFCStatementParser()
        with pytest.raises(UnrecognizedStatementFormatError):
            parser.parse(_fixture_bytes("other_bank_statement.pdf"), "irrelevant")

    def test_parse_indian_number_format(self):
        parser = HDFCStatementParser()
        result = parser.parse(_fixture_bytes("hdfc_statement_large_amount.pdf"), TEST_PDF_PASSWORD)

        assert result.closing_balance == Decimal("1234567.89")

    def test_parse_missing_closing_balance_line(self):
        parser = HDFCStatementParser()
        with pytest.raises(UnrecognizedStatementFormatError) as exc_info:
            parser.parse(_fixture_bytes("hdfc_statement_missing_balance.pdf"), TEST_PDF_PASSWORD)

        assert "closing balance" in str(exc_info.value).lower()

    def test_account_number_last4_derivation(self):
        parser = HDFCStatementParser()
        result = parser.parse(_fixture_bytes("hdfc_statement_valid.pdf"), TEST_PDF_PASSWORD)

        assert result.account_number is not None
        assert result.account_number_last4 == result.account_number[-4:]


class TestStatementParserRegistry:
    def test_list_supported_banks(self):
        assert list_supported_banks() == ["HDFC"]

    def test_get_parser_returns_hdfc_parser(self):
        parser = get_parser("HDFC")
        assert isinstance(parser, HDFCStatementParser)

    def test_get_parser_is_case_insensitive(self):
        parser = get_parser("hdfc")
        assert isinstance(parser, HDFCStatementParser)

    def test_get_parser_unsupported_bank_raises(self):
        with pytest.raises(UnsupportedBankError):
            get_parser("SBI")
