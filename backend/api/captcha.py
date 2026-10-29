import httpx

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, secret: str, transport: httpx.AsyncBaseTransport | None = None) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=transport) as client:
            response = await client.post(VERIFY_URL, data={"secret": secret, "response": token})
        return response.status_code == 200 and response.json().get("success") is True
    except (httpx.HTTPError, ValueError):
        return False
