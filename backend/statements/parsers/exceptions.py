class StatementParseError(Exception):
    """Base class for all statement parsing errors."""


class IncorrectPasswordError(StatementParseError):
    def __init__(self) -> None:
        super().__init__("Incorrect password for the uploaded PDF.")


class InvalidPDFError(StatementParseError):
    def __init__(self, detail: str = "The uploaded file is not a valid PDF.") -> None:
        super().__init__(detail)


class UnsupportedBankError(StatementParseError):
    def __init__(self, bank_code: str) -> None:
        self.bank_code = bank_code
        super().__init__(f"Unsupported bank: {bank_code}")


class UnrecognizedStatementFormatError(StatementParseError):
    def __init__(
        self,
        detail: str = "The PDF does not look like a statement we recognize for this bank.",
    ) -> None:
        super().__init__(detail)
