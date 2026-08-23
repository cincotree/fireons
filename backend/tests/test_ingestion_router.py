import ingestion.router as router_module
from tests.evals.fixtures.generate_eval_fixtures import FIXTURES_DIR, TEST_PDF_PASSWORD


def test_router_uses_parser_for_recognized_format_without_calling_llm(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("LLM path should not be called for a recognized format")

    monkeypatch.setattr(router_module, "extract_facts_from_text", _fail)

    pdf_bytes = (FIXTURES_DIR / "hdfc_2026_07.pdf").read_bytes()
    facts = router_module.route_extract(pdf_bytes, TEST_PDF_PASSWORD)

    assert facts["document_type"] == "bank_statement"
    assert facts["holdings"][0]["institution"] == "HDFC"


def test_router_falls_back_to_llm_for_unrecognized_format(monkeypatch):
    called = {}

    def _fake_llm(text: str) -> dict:
        called["yes"] = True
        return {
            "document_type": "unrecognized",
            "doc_issued_at": None,
            "investor_name": None,
            "source": None,
            "is_exhaustive": None,
            "holdings": [],
        }

    monkeypatch.setattr(router_module, "extract_facts_from_text", _fake_llm)

    pdf_bytes = (FIXTURES_DIR / "unknown_document.pdf").read_bytes()
    facts = router_module.route_extract(pdf_bytes, TEST_PDF_PASSWORD)

    assert called.get("yes") is True
    assert facts["document_type"] == "unrecognized"
