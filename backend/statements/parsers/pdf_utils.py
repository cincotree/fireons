from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from statements.parsers.exceptions import IncorrectPasswordError, InvalidPDFError


def decrypt_and_extract_text(pdf_bytes: bytes, password: str) -> str:
    """Open a (possibly password-protected) PDF and return its concatenated text.

    Works for unencrypted PDFs too (password is simply ignored in that case),
    so callers don't need to know up front whether the file is protected.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except (PdfReadError, ValueError) as exc:
        raise InvalidPDFError(f"Could not read PDF: {exc}") from exc

    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == 0:
            raise IncorrectPasswordError()

    try:
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise InvalidPDFError(f"Could not extract text from PDF: {exc}") from exc

    return "\n".join(pages_text)
