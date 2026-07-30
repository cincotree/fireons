from statements.parsers.base import BankStatementParser
from statements.parsers.exceptions import UnsupportedBankError
from statements.parsers.hdfc import HDFCStatementParser

_PARSERS: dict[str, type[BankStatementParser]] = {
    "HDFC": HDFCStatementParser,
}


def get_parser(bank_code: str) -> BankStatementParser:
    parser_cls = _PARSERS.get(bank_code.upper())
    if parser_cls is None:
        raise UnsupportedBankError(bank_code)
    return parser_cls()


def list_supported_banks() -> list[str]:
    return sorted(_PARSERS.keys())
