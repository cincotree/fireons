import json

import httpx
import pytest

import ingestion.extract as extract_module
from ingestion.config import Settings
from ingestion.extract import (
    EXTRACT_TOOL,
    ExtractionTruncatedError,
    begin_usage_tracking,
    end_usage_tracking,
    extract_facts_from_text,
)
from ingestion.llm_client import (
    AnthropicExtractor,
    LLMProviderError,
    OpenRouterExtractor,
    build_extractor,
)

TOOL_NAME = EXTRACT_TOOL["name"]


@pytest.fixture(autouse=True)
def _isolate_llm_env(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def _tool_call_body(arguments, *, finish_reason="tool_calls", usage=None, name=TOOL_NAME) -> dict:
    raw_arguments = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": name, "arguments": raw_arguments},
                        }
                    ],
                },
            }
        ],
        "usage": usage
        if usage is not None
        else {"prompt_tokens": 1000, "completion_tokens": 200, "cost": 0.0075},
    }


class _Recorder:
    def __init__(self, responses: list[httpx.Response]):
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responses.pop(0)


def _extractor(responses: list[httpx.Response], model: str = "anthropic/claude-sonnet-5"):
    recorder = _Recorder(responses)
    extractor = OpenRouterExtractor(
        api_key="test-key",
        model=model,
        base_url="https://openrouter.test/api/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(recorder)),
        retry_delays=(0, 0),
    )
    return extractor, recorder


def _call(extractor: OpenRouterExtractor):
    return extractor.call_tool(
        system="system prompt", tool=EXTRACT_TOOL, user_text="statement text", max_tokens=16384
    )


def test_build_extractor_defaults_to_anthropic():
    extractor = build_extractor(_settings(anthropic_api_key="a-key"))
    assert isinstance(extractor, AnthropicExtractor)
    assert extractor.model == "claude-sonnet-5"


def test_build_extractor_selects_openrouter():
    extractor = build_extractor(
        _settings(llm_provider="openrouter", openrouter_api_key="o-key", openrouter_model="openai/gpt-5")
    )
    assert isinstance(extractor, OpenRouterExtractor)
    assert extractor.model == "openai/gpt-5"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        _settings(llm_provider="somebody-else")


def test_settings_report_active_model_and_configuration():
    anthropic_settings = _settings(anthropic_api_key="a-key", openrouter_api_key="")
    assert anthropic_settings.active_model == "claude-sonnet-5"
    assert anthropic_settings.llm_configured

    openrouter_settings = _settings(llm_provider="openrouter", anthropic_api_key="a-key", openrouter_api_key="")
    assert openrouter_settings.active_model == "anthropic/claude-sonnet-5"
    assert not openrouter_settings.llm_configured


def test_request_forces_tool_and_restricts_providers():
    extractor, recorder = _extractor([httpx.Response(200, json=_tool_call_body({"document_type": "x"}))])
    _call(extractor)

    request = recorder.requests[0]
    assert str(request.url) == "https://openrouter.test/api/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "anthropic/claude-sonnet-5"
    assert body["max_tokens"] == 16384
    assert body["tools"][0]["function"]["name"] == TOOL_NAME
    assert body["tools"][0]["function"]["parameters"] == EXTRACT_TOOL["input_schema"]
    assert body["tool_choice"] == {"type": "function", "function": {"name": TOOL_NAME}}
    assert body["provider"] == {"require_parameters": True, "data_collection": "deny"}
    assert body["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert body["messages"][1] == {"role": "user", "content": "statement text"}


def test_cache_control_only_sent_for_anthropic_models():
    extractor, recorder = _extractor(
        [httpx.Response(200, json=_tool_call_body({"document_type": "x"}))], model="openai/gpt-5"
    )
    _call(extractor)
    body = json.loads(recorder.requests[0].content)
    assert "cache_control" not in body["messages"][0]["content"][0]


def test_successful_tool_call_returns_arguments_and_usage():
    extractor, _ = _extractor(
        [
            httpx.Response(
                200,
                json=_tool_call_body(
                    {"document_type": "bank_statement"},
                    usage={
                        "prompt_tokens": 1500,
                        "completion_tokens": 300,
                        "prompt_tokens_details": {"cached_tokens": 1000, "cache_write_tokens": 200},
                        "cost": 0.0123,
                    },
                ),
            )
        ]
    )
    result = _call(extractor)

    assert result.tool_input == {"document_type": "bank_statement"}
    assert not result.truncated
    assert result.usage.input_tokens == 300
    assert result.usage.output_tokens == 300
    assert result.usage.cache_read_input_tokens == 1000
    assert result.usage.cache_creation_input_tokens == 200
    assert result.usage.cost_usd == pytest.approx(0.0123)


def test_length_finish_reason_is_truncation():
    extractor, _ = _extractor(
        [httpx.Response(200, json=_tool_call_body('{"document_type": "ba', finish_reason="length"))]
    )
    result = _call(extractor)
    assert result.truncated
    assert result.tool_input is None


def test_missing_tool_call_returns_no_input():
    body = {
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Sorry"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }
    extractor, _ = _extractor([httpx.Response(200, json=body)])
    result = _call(extractor)
    assert result.tool_input is None
    assert not result.truncated
    assert result.usage.cost_usd is None


def test_tool_call_for_another_function_is_ignored():
    extractor, _ = _extractor(
        [httpx.Response(200, json=_tool_call_body({"document_type": "x"}, name="something_else"))]
    )
    assert _call(extractor).tool_input is None


def test_invalid_json_arguments_raise():
    extractor, _ = _extractor([httpx.Response(200, json=_tool_call_body("{not json"))])
    with pytest.raises(ValueError, match="not valid JSON"):
        _call(extractor)


def test_non_object_arguments_raise():
    extractor, _ = _extractor([httpx.Response(200, json=_tool_call_body("[1, 2]"))])
    with pytest.raises(ValueError, match="not a JSON object"):
        _call(extractor)


def test_client_error_is_not_retried():
    extractor, recorder = _extractor(
        [httpx.Response(401, json={"error": {"code": 401, "message": "No auth credentials found"}})]
    )
    with pytest.raises(LLMProviderError, match="HTTP 401: No auth credentials found"):
        _call(extractor)
    assert len(recorder.requests) == 1


def test_error_message_never_contains_api_key():
    extractor, _ = _extractor([httpx.Response(400, text="bad request")])
    with pytest.raises(LLMProviderError) as error:
        _call(extractor)
    assert "test-key" not in str(error.value)


def test_retryable_status_is_retried_then_succeeds():
    extractor, recorder = _extractor(
        [
            httpx.Response(429, json={"error": {"code": 429, "message": "Rate limited"}}),
            httpx.Response(503, text="unavailable"),
            httpx.Response(200, json=_tool_call_body({"document_type": "x"})),
        ]
    )
    assert _call(extractor).tool_input == {"document_type": "x"}
    assert len(recorder.requests) == 3


def test_retryable_status_gives_up_after_last_attempt():
    extractor, recorder = _extractor([httpx.Response(502, text="bad gateway")] * 3)
    with pytest.raises(LLMProviderError, match="HTTP 502"):
        _call(extractor)
    assert len(recorder.requests) == 3


def test_transport_error_is_retried_then_raised():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("connection refused", request=request)

    extractor = OpenRouterExtractor(
        api_key="test-key",
        model="anthropic/claude-sonnet-5",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry_delays=(0, 0),
    )
    with pytest.raises(LLMProviderError, match="ConnectError"):
        _call(extractor)
    assert len(calls) == 3


def test_error_in_successful_response_body_raises():
    extractor, _ = _extractor(
        [httpx.Response(200, json={"error": {"code": 502, "message": "Upstream provider failed"}})]
    )
    with pytest.raises(LLMProviderError, match="Upstream provider failed"):
        _call(extractor)


def test_error_on_choice_raises():
    body = {"choices": [{"finish_reason": "error", "error": {"message": "Provider crashed"}, "message": {}}]}
    extractor, _ = _extractor([httpx.Response(200, json=body)])
    with pytest.raises(LLMProviderError, match="Provider crashed"):
        _call(extractor)


def test_non_json_response_raises():
    extractor, _ = _extractor([httpx.Response(200, text="<html>oops</html>")])
    with pytest.raises(LLMProviderError, match="not JSON"):
        _call(extractor)


def test_extract_facts_from_text_through_openrouter(monkeypatch):
    extractor, _ = _extractor(
        [httpx.Response(200, json=_tool_call_body({"document_type": "bank_statement"}))]
    )
    monkeypatch.setattr(extract_module, "get_extractor", lambda: extractor)

    token = begin_usage_tracking()
    facts = extract_facts_from_text("openrouter statement text that never hits the cache")
    usage = end_usage_tracking(token)

    assert facts == {"document_type": "bank_statement"}
    assert len(usage) == 1
    assert usage[0].cost_usd == pytest.approx(0.0075)


def test_extract_facts_from_text_truncated_through_openrouter(monkeypatch):
    extractor, _ = _extractor(
        [httpx.Response(200, json=_tool_call_body('{"document', finish_reason="length"))]
    )
    monkeypatch.setattr(extract_module, "get_extractor", lambda: extractor)

    with pytest.raises(ExtractionTruncatedError):
        extract_facts_from_text("openrouter statement text that never hits the cache — truncated")


def test_openrouter_mode_does_not_import_anthropic_sdk():
    import subprocess
    import sys

    code = (
        "import sys;"
        "from ingestion.config import Settings;"
        "from ingestion.llm_client import build_extractor;"
        "build_extractor(Settings(_env_file=None, llm_provider='openrouter', openrouter_api_key='k'));"
        "print('anthropic' in sys.modules)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PATH": ""})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
