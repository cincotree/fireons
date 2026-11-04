import httpx

SEARCH_URL = "https://api.tavily.com/search"
RESULTS_PER_SEARCH = 5


class TavilyError(RuntimeError):
    pass


class QuotaExhausted(TavilyError):
    pass


async def search(
    api_key: str,
    query: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[str]:
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
    return [item["url"] for item in response.json().get("results", []) if item.get("url")]
