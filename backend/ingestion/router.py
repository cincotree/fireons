from ingestion.extract import extract_facts_from_text, read_pdf_text
from ingestion.parsers import PARSERS


def route_extract(pdf_bytes: bytes, password: str | None = None) -> dict:
    text = read_pdf_text(pdf_bytes, password)
    for try_parse in PARSERS:
        facts = try_parse(text)
        if facts is not None:
            return facts
    return extract_facts_from_text(text)
