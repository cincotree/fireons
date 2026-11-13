import csv
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

from enrichment.places_cities import CITIES

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
QUOTA_TIMEZONE = ZoneInfo("America/Los_Angeles")
PAGE_SIZE = 20
DEFAULT_MAX_PAGES = 3
REQUEST_PAUSE_SECONDS = 0.3

PRO_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.businessStatus",
    "places.googleMapsUri",
]
ENTERPRISE_FIELDS = PRO_FIELDS + ["places.nationalPhoneNumber", "places.websiteUri"]
TIERS = {
    "pro": {"fields": PRO_FIELDS, "monthly_free_calls": 5000},
    "enterprise": {"fields": ENTERPRISE_FIELDS, "monthly_free_calls": 1000},
}

CATEGORIES = {
    "chartered_accountant": "chartered accountant",
    "tax_consultant": "tax consultant",
    "financial_planner": "financial planner",
    "wealth_manager": "wealth manager",
    "investment_advisor": "investment advisor",
    "insurance_advisor": "insurance advisor",
    "estate_planner": "estate planning lawyer",
}

CSV_COLUMNS = [
    "place_id",
    "name",
    "category",
    "searched_city",
    "address",
    "latitude",
    "longitude",
    "phone",
    "website",
    "google_maps_url",
    "business_status",
    "types",
    "fetched_at",
]


class PlacesError(RuntimeError):
    pass


@dataclass
class ExportSummary:
    calls_made: int = 0
    places_written: int = 0
    duplicates_skipped: int = 0
    queries_completed: int = 0
    queries_remaining: int = 0
    stopped_reason: str = "finished"
    calls_left_today: int = 0
    calls_left_this_month: int = 0
    errors: list[str] = field(default_factory=list)


def quota_day(now: datetime) -> str:
    return now.astimezone(QUOTA_TIMEZONE).strftime("%Y-%m-%d")


def quota_month(now: datetime) -> str:
    return now.astimezone(QUOTA_TIMEZONE).strftime("%Y-%m")


class UsageLedger:
    def __init__(self, path: Path, daily_limit: int, monthly_limit: int):
        self.path = path
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.state = {"days": {}, "months": {}}
        if path.exists():
            self.state.update(json.loads(path.read_text(encoding="utf-8")))

    def used_today(self, now: datetime) -> int:
        return int(self.state["days"].get(quota_day(now), 0))

    def used_this_month(self, now: datetime) -> int:
        return int(self.state["months"].get(quota_month(now), 0))

    def left_today(self, now: datetime) -> int:
        return max(self.daily_limit - self.used_today(now), 0)

    def left_this_month(self, now: datetime) -> int:
        return max(self.monthly_limit - self.used_this_month(now), 0)

    def remaining(self, now: datetime) -> int:
        return min(self.left_today(now), self.left_this_month(now))

    def record_call(self, now: datetime) -> None:
        day, month = quota_day(now), quota_month(now)
        self.state["days"][day] = self.used_today(now) + 1
        self.state["months"][month] = self.used_this_month(now) + 1
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)


class Progress:
    def __init__(self, path: Path):
        self.path = path
        self.state = {"done": [], "pending": {}}
        if path.exists():
            self.state.update(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)


def default_daily_limit(monthly_free_calls: int) -> int:
    return monthly_free_calls // 31


def build_queries(categories: list[str], cities: list[str]) -> list[tuple[str, str, str]]:
    return [
        (f"{category}|{city}", category, city)
        for city in cities
        for category in categories
    ]


def _existing_place_ids(output: Path) -> set[str]:
    if not output.exists():
        return set()
    with output.open(newline="", encoding="utf-8") as handle:
        return {row["place_id"] for row in csv.DictReader(handle)}


def _row(place: dict, category: str, city: str, fetched_at: str) -> dict:
    location = place.get("location") or {}
    return {
        "place_id": place.get("id", ""),
        "name": (place.get("displayName") or {}).get("text", ""),
        "category": category,
        "searched_city": city,
        "address": place.get("formattedAddress", ""),
        "latitude": location.get("latitude", ""),
        "longitude": location.get("longitude", ""),
        "phone": place.get("nationalPhoneNumber", ""),
        "website": place.get("websiteUri", ""),
        "google_maps_url": place.get("googleMapsUri", ""),
        "business_status": place.get("businessStatus", ""),
        "types": ";".join(place.get("types", [])),
        "fetched_at": fetched_at,
    }


def _search(
    client: httpx.Client,
    api_key: str,
    fields: list[str],
    text_query: str,
    page_token: str | None,
) -> dict:
    body = {"textQuery": text_query, "pageSize": PAGE_SIZE, "regionCode": "IN", "languageCode": "en"}
    if page_token:
        body["pageToken"] = page_token
    response = client.post(
        SEARCH_URL,
        json=body,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": ",".join(fields + ["nextPageToken"]),
        },
    )
    if response.status_code == 429:
        raise PlacesError("rate-limited")
    if response.status_code >= 500:
        raise PlacesError(f"server-error {response.status_code}")
    if response.status_code != 200:
        message = ""
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            message = response.text[:200]
        raise PlacesError(f"HTTP {response.status_code}: {message}")
    return response.json()


def run_export(
    output: Path,
    api_key: str,
    tier: str = "pro",
    daily_limit: int | None = None,
    monthly_limit: int | None = None,
    categories: list[str] | None = None,
    cities: list[str] | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
    client: httpx.Client | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(QUOTA_TIMEZONE),
    sleep: Callable[[float], None] = time.sleep,
) -> ExportSummary:
    if not api_key:
        raise PlacesError("GOOGLE_API_KEY is not set")
    tier_config = TIERS[tier]
    monthly = monthly_limit if monthly_limit is not None else tier_config["monthly_free_calls"]
    daily = daily_limit if daily_limit is not None else default_daily_limit(tier_config["monthly_free_calls"])
    unknown = [c for c in (categories or []) if c not in CATEGORIES]
    if unknown:
        raise PlacesError(f"Unknown categories: {', '.join(unknown)}")
    chosen_categories = categories or list(CATEGORIES)
    chosen_cities = cities or CITIES

    ledger = UsageLedger(output.parent / "places_usage.json", daily, monthly)
    progress = Progress(output.with_name(output.stem + ".progress.json"))
    seen_ids = _existing_place_ids(output)
    work = [item for item in build_queries(chosen_categories, chosen_cities) if item[0] not in progress.state["done"]]
    summary = ExportSummary()
    owns_client = client is None
    http = client or httpx.Client(timeout=30.0)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output.exists()

    try:
        with output.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            if write_header:
                writer.writeheader()
            for key, category, city in work:
                pending = progress.state["pending"].get(key, {"token": None, "pages": 0})
                while True:
                    moment = now()
                    if ledger.remaining(moment) <= 0:
                        summary.stopped_reason = (
                            "daily quota reached" if ledger.left_today(moment) <= 0 else "monthly quota reached"
                        )
                        break
                    ledger.record_call(moment)
                    summary.calls_made += 1
                    try:
                        data = _search(
                            http,
                            api_key,
                            tier_config["fields"],
                            f"{CATEGORIES[category]} in {city}, India",
                            pending["token"],
                        )
                    except PlacesError as exc:
                        if str(exc).startswith(("rate-limited", "server-error")):
                            summary.stopped_reason = f"stopped: {exc}"
                            break
                        raise
                    fetched_at = moment.isoformat(timespec="seconds")
                    for place in data.get("places", []):
                        place_id = place.get("id")
                        if not place_id or place_id in seen_ids:
                            summary.duplicates_skipped += 1
                            continue
                        seen_ids.add(place_id)
                        writer.writerow(_row(place, category, city, fetched_at))
                        summary.places_written += 1
                    handle.flush()
                    pending = {"token": data.get("nextPageToken"), "pages": pending["pages"] + 1}
                    if not pending["token"] or pending["pages"] >= max_pages:
                        progress.state["pending"].pop(key, None)
                        progress.state["done"].append(key)
                        progress.save()
                        summary.queries_completed += 1
                        break
                    progress.state["pending"][key] = pending
                    progress.save()
                    sleep(REQUEST_PAUSE_SECONDS)
                if summary.stopped_reason != "finished":
                    break
                sleep(REQUEST_PAUSE_SECONDS)
    finally:
        if owns_client:
            http.close()

    moment = now()
    summary.queries_remaining = len(work) - summary.queries_completed
    summary.calls_left_today = ledger.left_today(moment)
    summary.calls_left_this_month = ledger.left_this_month(moment)
    return summary
