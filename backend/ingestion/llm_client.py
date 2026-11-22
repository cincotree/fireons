import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from ingestion.config import Settings, get_settings

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
_OPENROUTER_TIMEOUT_SECONDS = 300.0


@dataclass
class ExtractionUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    cost_usd: float | None = None


@dataclass
class ToolCallResult:
    tool_input: dict | None
    truncated: bool
    usage: ExtractionUsage


class LLMProviderError(Exception):
    pass


class ToolCallingExtractor(Protocol):
    provider: str
    model: str

    def call_tool(self, system: str, tool: dict, user_text: str, max_tokens: int) -> ToolCallResult: ...


class AnthropicExtractor:
    provider = "anthropic"

    def __init__(self, client: Any, model: str):
        self._client = client
        self.model = model

    def call_tool(self, system: str, tool: dict, user_text: str, max_tokens: int) -> ToolCallResult:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=[{**tool, "cache_control": {"type": "ephemeral"}}],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_text}],
        )
        usage = ExtractionUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens or 0,
            cache_read_input_tokens=response.usage.cache_read_input_tokens or 0,
        )
        tool_input = next(
            (block.input for block in response.content if block.type == "tool_use"),
            None,
        )
        return ToolCallResult(
            tool_input=tool_input,
            truncated=response.stop_reason == "max_tokens",
            usage=usage,
        )


class OpenRouterExtractor:
    provider = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        http_client: httpx.Client | None = None,
        retry_delays: tuple[float, ...] = (1.0, 4.0),
    ):
        self._api_key = api_key
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client(timeout=_OPENROUTER_TIMEOUT_SECONDS)
        self._retry_delays = retry_delays

    def build_request(self, system: str, tool: dict, user_text: str, max_tokens: int) -> dict:
        system_part: dict = {"type": "text", "text": system}
        if self.model.startswith("anthropic/"):
            system_part["cache_control"] = {"type": "ephemeral"}
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": [system_part]},
                {"role": "user", "content": user_text},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": tool["name"]}},
            "provider": {"require_parameters": True, "data_collection": "deny"},
            "usage": {"include": True},
        }

    def call_tool(self, system: str, tool: dict, user_text: str, max_tokens: int) -> ToolCallResult:
        body = self._post(self.build_request(system, tool, user_text, max_tokens))
        return self.parse_response(body, tool["name"])

    def _post(self, payload: dict) -> dict:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        attempts = len(self._retry_delays) + 1
        for attempt in range(attempts):
            is_last = attempt == attempts - 1
            try:
                response = self._http.post(url, json=payload, headers=headers)
            except httpx.TransportError as error:
                if is_last:
                    raise LLMProviderError(f"OpenRouter request failed: {type(error).__name__}") from error
                time.sleep(self._retry_delays[attempt])
                continue
            if response.status_code in _RETRYABLE_STATUS and not is_last:
                time.sleep(self._retry_delays[attempt])
                continue
            if response.status_code >= 400:
                raise LLMProviderError(
                    f"OpenRouter returned HTTP {response.status_code}: {_error_message(response)}"
                )
            try:
                return response.json()
            except ValueError as error:
                raise LLMProviderError("OpenRouter returned a response that is not JSON") from error
        raise LLMProviderError("OpenRouter request failed")

    @staticmethod
    def parse_response(body: dict, tool_name: str) -> ToolCallResult:
        if body.get("error"):
            raise LLMProviderError(f"OpenRouter returned an error: {_describe_error(body['error'])}")
        choices = body.get("choices") or []
        if not choices:
            raise LLMProviderError("OpenRouter returned no choices")
        choice = choices[0]
        if choice.get("error"):
            raise LLMProviderError(f"OpenRouter returned an error: {_describe_error(choice['error'])}")

        usage = _openrouter_usage(body.get("usage") or {})
        if choice.get("finish_reason") == "length":
            return ToolCallResult(tool_input=None, truncated=True, usage=usage)

        tool_calls = (choice.get("message") or {}).get("tool_calls") or []
        for call in tool_calls:
            function = call.get("function") or {}
            if function.get("name") != tool_name:
                continue
            try:
                arguments = json.loads(function.get("arguments") or "")
            except json.JSONDecodeError as error:
                raise ValueError("Model returned tool arguments that are not valid JSON") from error
            if not isinstance(arguments, dict):
                raise ValueError("Model returned tool arguments that are not a JSON object")
            return ToolCallResult(tool_input=arguments, truncated=False, usage=usage)
        return ToolCallResult(tool_input=None, truncated=False, usage=usage)


def _openrouter_usage(usage: dict) -> ExtractionUsage:
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens") or 0
    cache_write = details.get("cache_write_tokens") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    cost = usage.get("cost")
    return ExtractionUsage(
        input_tokens=max(prompt_tokens - cached - cache_write, 0),
        output_tokens=usage.get("completion_tokens") or 0,
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cached,
        cost_usd=float(cost) if cost is not None else None,
    )


def _describe_error(error: Any) -> str:
    if isinstance(error, dict):
        message = error.get("message") or "unknown error"
        code = error.get("code")
        return f"{message} (code {code})" if code is not None else str(message)
    return str(error)


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.reason_phrase or "unknown error"
    if isinstance(body, dict) and body.get("error"):
        return _describe_error(body["error"])
    return response.reason_phrase or "unknown error"


def build_extractor(settings: Settings) -> ToolCallingExtractor:
    if settings.llm_provider == "openrouter":
        return OpenRouterExtractor(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
        )
    import anthropic

    return AnthropicExtractor(
        client=anthropic.Anthropic(api_key=settings.anthropic_api_key),
        model=settings.anthropic_model,
    )


_extractor: ToolCallingExtractor | None = None


def get_extractor() -> ToolCallingExtractor:
    global _extractor
    if _extractor is None:
        _extractor = build_extractor(get_settings())
    return _extractor
