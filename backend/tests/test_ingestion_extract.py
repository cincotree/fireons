from dataclasses import dataclass, field
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

import ingestion.extract as extract_module
from ingestion.extract import (
    ExtractionTruncatedError,
    begin_usage_tracking,
    end_usage_tracking,
    estimate_cost_usd,
    extract_facts_from_text,
    read_pdf_text,
)


@dataclass
class _FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _FakeToolUseBlock:
    input: dict
    type: str = "tool_use"


@dataclass
class _FakeResponse:
    stop_reason: str
    content: list = field(default_factory=list)
    usage: _FakeUsage = field(default_factory=_FakeUsage)


class _FakeMessages:
    def __init__(self, response: _FakeResponse):
        self._response = response

    def create(self, **kwargs) -> _FakeResponse:
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self.messages = _FakeMessages(response)


def test_max_tokens_stop_reason_raises_truncated_error(monkeypatch):
    """A response cut off by the output budget must be reported distinctly from
    a generically malformed result — the document itself is fine, it just has
    more holdings than fit in one pass. Confirmed happening in practice with a
    real, comprehensive multi-folio statement."""
    fake_response = _FakeResponse(stop_reason="max_tokens", content=[])
    monkeypatch.setattr(extract_module, "get_client", lambda: _FakeClient(fake_response))

    with pytest.raises(ExtractionTruncatedError):
        extract_facts_from_text("some statement text that never hits the cache")


def _render_pdf_bytes(text: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(72, 720, text)
    c.save()
    return buffer.getvalue()


def _encrypted_pdf_bytes(text: str, user_password: str, owner_password: str) -> bytes:
    reader = PdfReader(BytesIO(_render_pdf_bytes(text)))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=user_password, owner_password=owner_password)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def test_read_pdf_text_unencrypted():
    pdf_bytes = _render_pdf_bytes("plain statement text")
    assert "plain statement text" in read_pdf_text(pdf_bytes, password=None)


def test_read_pdf_text_with_real_user_password():
    pdf_bytes = _encrypted_pdf_bytes(
        "password protected text", user_password="Secret123", owner_password="OwnerSecret456"
    )
    assert "password protected text" in read_pdf_text(pdf_bytes, password="Secret123")


def test_read_pdf_text_owner_password_only_needs_no_password():
    """A statement encrypted with an empty user password (owner-password-only,
    restricting printing/editing but not requiring a password to open) must
    extract cleanly with no password supplied — this is the real-world shape
    of many bank statement PDFs, and previously fell back to a hardcoded
    eval-only password that doesn't match, breaking extraction."""
    pdf_bytes = _encrypted_pdf_bytes(
        "owner protected only", user_password="", owner_password="OwnerSecret456"
    )
    assert "owner protected only" in read_pdf_text(pdf_bytes, password=None)


def test_extract_facts_from_text_records_usage_when_tracking_active(monkeypatch):
    fake_response = _FakeResponse(
        stop_reason="tool_use",
        content=[_FakeToolUseBlock(input={"document_type": "bank_statement"})],
        usage=_FakeUsage(
            input_tokens=120,
            output_tokens=45,
            cache_creation_input_tokens=800,
            cache_read_input_tokens=0,
        ),
    )
    monkeypatch.setattr(extract_module, "get_client", lambda: _FakeClient(fake_response))

    token = begin_usage_tracking()
    extract_facts_from_text("some statement text that never hits the cache — usage test")
    usage = end_usage_tracking(token)

    assert len(usage) == 1
    assert usage[0].input_tokens == 120
    assert usage[0].output_tokens == 45
    assert usage[0].cache_creation_input_tokens == 800
    assert usage[0].cache_read_input_tokens == 0


def test_extract_facts_from_text_records_nothing_without_active_tracking(monkeypatch):
    """Regression guard: begin_usage_tracking()/end_usage_tracking() must fully
    restore the ContextVar via a token, not just set() it — otherwise a call to
    extract_facts_from_text() from code that never started tracking (e.g. a
    test, or any future direct caller) sees stale state left behind by an
    earlier, unrelated tracked call in the same thread and blows up trying to
    read .usage off a response that was never meant to be tracked."""
    token = begin_usage_tracking()
    end_usage_tracking(token)  # simulates an earlier, unrelated tracked call completing

    fake_response = _FakeResponse(stop_reason="max_tokens", content=[])
    monkeypatch.setattr(extract_module, "get_client", lambda: _FakeClient(fake_response))

    with pytest.raises(ExtractionTruncatedError):
        extract_facts_from_text("some statement text that never hits the cache — leak test")


def test_estimate_cost_usd_known_model():
    usage = [
        extract_module.ExtractionUsage(
            input_tokens=1000,
            output_tokens=1000,
            cache_creation_input_tokens=1000,
            cache_read_input_tokens=1000,
        )
    ]
    cost = estimate_cost_usd(usage, "claude-sonnet-5")
    input_price, output_price = 3.00, 15.00
    expected = (
        1000 * input_price + 1000 * input_price * 1.25 + 1000 * input_price * 0.1 + 1000 * output_price
    ) / 1_000_000
    assert cost == pytest.approx(expected)


def test_estimate_cost_usd_unknown_model_returns_none():
    usage = [extract_module.ExtractionUsage(1000, 1000, 0, 0)]
    assert estimate_cost_usd(usage, "some-future-model") is None
