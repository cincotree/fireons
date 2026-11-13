from typing import Optional

import httpx
from pydantic import BaseModel

DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = "displayName,formattedAddress,googleMapsUri"
TIMEOUT_SECONDS = 5.0


class GooglePlaceDetails(BaseModel):
    name: Optional[str]
    address: Optional[str]
    maps_url: Optional[str]


class PlaceDetailsUnavailable(RuntimeError):
    pass


async def fetch_place_details(
    api_key: str, place_id: str, transport: httpx.AsyncBaseTransport | None = None
) -> GooglePlaceDetails:
    if not api_key:
        raise PlaceDetailsUnavailable("GOOGLE_API_KEY is not set")
    try:
        async with httpx.AsyncClient(transport=transport, timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(
                DETAILS_URL.format(place_id=place_id),
                headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK},
            )
    except httpx.HTTPError as exc:
        raise PlaceDetailsUnavailable(type(exc).__name__) from None
    if response.status_code >= 400:
        raise PlaceDetailsUnavailable(f"Google returned {response.status_code}")
    body = response.json()
    return GooglePlaceDetails(
        name=(body.get("displayName") or {}).get("text"),
        address=body.get("formattedAddress"),
        maps_url=body.get("googleMapsUri"),
    )
