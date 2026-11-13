from dataclasses import dataclass

import httpx

SEARCH_URL = "https://api.tavily.com/search"
RESULTS_PER_SEARCH = 5


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str


class TavilyError(RuntimeError):
    pass


class QuotaExhausted(TavilyError):
    pass


async def search(
    api_key: str,
    query: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[str]:
    return [result.url for result in await search_results(api_key, query, transport)]


async def search_results(
    api_key: str,
    query: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[SearchResult]:
    if not api_key:
        raise TavilyError("TAVILY_API_KEY is not set")
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        try:
            response = await client.post(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": RESULTS_PER_SEARCH,
                    "include_answer": False,
                },
            )
        except httpx.TransportError as exc:
            raise TavilyError(f"Tavily request failed: {type(exc).__name__}") from None
    if response.status_code in {429, 432, 433}:
        raise QuotaExhausted(f"Tavily returned {response.status_code}")
    if response.status_code >= 400:
        raise TavilyError(f"Tavily returned {response.status_code}")
    return [
        SearchResult(url=item["url"], title=(item.get("title") or "").strip())
        for item in response.json().get("results", [])
        if item.get("url")
    ]
