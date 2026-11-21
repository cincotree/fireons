import csv
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

from enrichment.places import (
    CATEGORIES,
    CSV_COLUMNS,
    ENTERPRISE_FIELDS,
    PRO_FIELDS,
    PlacesError,
    default_daily_limit,
    quota_day,
    run_export,
)
from enrichment.places_cities import CITIES

KEY = "test-key-123"
PT = ZoneInfo("America/Los_Angeles")
DAY1 = datetime(2026, 11, 3, 10, 0, tzinfo=PT)


def place(number: int, name: str | None = None) -> dict:
    return {
        "id": f"place-{number}",
        "displayName": {"text": name or f"Sample Advisers {number}"},
        "formattedAddress": f"{number} Test Road, Testville, India",
        "location": {"latitude": 12.5, "longitude": 77.5},
        "types": ["accounting", "point_of_interest"],
        "businessStatus": "OPERATIONAL",
        "googleMapsUri": f"https://maps.example.test/{number}",
        "nationalPhoneNumber": "099999 00000",
        "websiteUri": f"https://firm{number}.example.com/",
    }


class FakePlaces:
    def __init__(self, pages: dict[str, list[list[dict]]] | None = None, status: int = 200):
        self.pages = pages or {}
        self.status = status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "billing not enabled"}})
        body = json.loads(request.content)
        pages = self.pages.get(body["textQuery"], [[place(1)]])
        index = int(body["pageToken"]) if body.get("pageToken") else 0
        payload = {"places": pages[index]}
        if index + 1 < len(pages):
            payload["nextPageToken"] = str(index + 1)
        return httpx.Response(200, json=payload)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def export(tmp_path, fake, now=lambda: DAY1, **kwargs):
    defaults = dict(
        output=tmp_path / "places.csv",
        api_key=KEY,
        categories=["chartered_accountant"],
        cities=["Testville"],
        client=fake.client(),
        now=now,
        sleep=lambda _: None,
    )
    defaults.update(kwargs)
    return run_export(**defaults)


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_key_goes_in_a_header_never_in_the_url(tmp_path):
    fake = FakePlaces()
    export(tmp_path, fake)

    request = fake.requests[0]
    assert request.headers["x-goog-api-key"] == KEY
    assert KEY not in str(request.url)
    assert request.url.query == b""


def test_pro_tier_does_not_request_contact_fields_and_enterprise_does(tmp_path):
    pro, enterprise = FakePlaces(), FakePlaces()
    export(tmp_path / "a", pro)
    export(tmp_path / "b", enterprise, tier="enterprise")

    pro_mask = pro.requests[0].headers["x-goog-fieldmask"].split(",")
    enterprise_mask = enterprise.requests[0].headers["x-goog-fieldmask"].split(",")
    assert set(pro_mask) == set(PRO_FIELDS) | {"nextPageToken"}
    assert "places.websiteUri" not in pro_mask
    assert set(ENTERPRISE_FIELDS) <= set(enterprise_mask)


def test_results_are_written_with_the_documented_columns(tmp_path):
    export(tmp_path, FakePlaces())

    [row] = rows(tmp_path / "places.csv")
    assert list(row) == CSV_COLUMNS
    assert row["name"] == "Sample Advisers 1"
    assert row["category"] == "chartered_accountant"
    assert row["searched_city"] == "Testville"
    assert row["website"] == "https://firm1.example.com/"
    assert row["types"] == "accounting;point_of_interest"
    assert row["fetched_at"].startswith("2026-11-03T10:00:00")


def test_query_is_built_from_category_and_city_for_india(tmp_path):
    fake = FakePlaces()
    export(tmp_path, fake, categories=["tax_consultant"], cities=["Pune"])

    body = json.loads(fake.requests[0].content)
    assert body["textQuery"] == "tax consultant in Pune, India"
    assert body["regionCode"] == "IN"
    assert body["pageSize"] == 20


def test_pagination_follows_tokens_until_exhausted_or_the_page_cap(tmp_path):
    query = "chartered accountant in Testville, India"
    pages = {query: [[place(1), place(2)], [place(3)], [place(4)], [place(5)]]}
    fake = FakePlaces(pages)

    summary = export(tmp_path, fake, max_pages=3)

    assert summary.calls_made == 3
    assert summary.places_written == 4
    assert summary.queries_completed == 1


def test_duplicates_within_and_across_runs_are_skipped(tmp_path):
    pages = {
        "chartered accountant in Testville, India": [[place(1), place(2)]],
        "tax consultant in Testville, India": [[place(2), place(3)]],
    }
    first = export(tmp_path, FakePlaces(pages), categories=["chartered_accountant", "tax_consultant"])
    second = export(tmp_path, FakePlaces(pages), categories=["chartered_accountant", "tax_consultant"])

    assert (first.places_written, first.duplicates_skipped) == (3, 1)
    assert second.calls_made == 0
    assert len(rows(tmp_path / "places.csv")) == 3


def test_header_is_written_once_across_runs(tmp_path):
    export(tmp_path, FakePlaces(), cities=["A"])
    export(tmp_path, FakePlaces({"chartered accountant in B, India": [[place(9)]]}), cities=["A", "B"])

    lines = (tmp_path / "places.csv").read_text(encoding="utf-8").splitlines()
    assert sum(1 for line in lines if line.startswith("place_id,")) == 1


def test_run_stops_at_the_daily_limit_and_resumes_the_next_day(tmp_path):
    fake = FakePlaces()
    cities = ["A", "B", "C", "D", "E"]
    pages = {f"chartered accountant in {c}, India": [[place(i)]] for i, c in enumerate(cities)}
    fake.pages = pages

    first = export(tmp_path, fake, cities=cities, daily_limit=2)
    same_day = export(tmp_path, fake, cities=cities, daily_limit=2)
    next_day = export(tmp_path, fake, cities=cities, daily_limit=2, now=lambda: DAY1 + timedelta(days=1))

    assert (first.calls_made, first.stopped_reason, first.queries_remaining) == (2, "daily quota reached", 3)
    assert (same_day.calls_made, same_day.stopped_reason) == (0, "daily quota reached")
    assert next_day.calls_made == 2
    assert len(rows(tmp_path / "places.csv")) == 4
    assert len(fake.requests) == 4


def test_monthly_limit_is_enforced_even_when_the_daily_limit_has_room(tmp_path):
    fake = FakePlaces()
    cities = ["A", "B", "C"]

    summary = export(tmp_path, fake, cities=cities, daily_limit=100, monthly_limit=2)

    assert summary.calls_made == 2
    assert summary.stopped_reason == "monthly quota reached"
    assert summary.calls_left_this_month == 0


def test_interrupted_pagination_resumes_from_the_saved_token(tmp_path):
    query = "chartered accountant in Testville, India"
    fake = FakePlaces({query: [[place(1)], [place(2)], [place(3)]]})

    first = export(tmp_path, fake, daily_limit=2)
    second = export(tmp_path, fake, daily_limit=2, now=lambda: DAY1 + timedelta(days=1))

    tokens = [json.loads(r.content).get("pageToken") for r in fake.requests]
    assert tokens == [None, "1", "2"]
    assert first.queries_completed == 0 and second.queries_completed == 1
    assert len(rows(tmp_path / "places.csv")) == 3


def test_every_attempted_call_counts_toward_the_quota_even_when_it_fails(tmp_path):
    fake = FakePlaces(status=429)

    summary = export(tmp_path, fake, daily_limit=5)

    assert summary.calls_made == 1
    assert summary.stopped_reason == "stopped: rate-limited"
    assert summary.calls_left_today == 4
    state = json.loads((tmp_path / "places_usage.json").read_text())
    assert state["days"][quota_day(DAY1)] == 1


def test_api_errors_such_as_billing_off_raise_without_leaking_the_key(tmp_path):
    fake = FakePlaces(status=403)

    with pytest.raises(PlacesError) as caught:
        export(tmp_path, fake)

    assert "billing not enabled" in str(caught.value)
    assert KEY not in str(caught.value)


def test_missing_key_and_unknown_category_are_rejected_before_any_call(tmp_path):
    fake = FakePlaces()

    with pytest.raises(PlacesError, match="not set"):
        export(tmp_path, fake, api_key="")
    with pytest.raises(PlacesError, match="Unknown categories"):
        export(tmp_path, fake, categories=["astrologer"])
    assert fake.requests == []


def test_default_daily_limit_keeps_a_month_inside_the_free_tier():
    assert default_daily_limit(5000) == 161
    assert default_daily_limit(1000) == 32
    assert default_daily_limit(5000) * 31 <= 5000


def test_quota_day_follows_pacific_time_like_google_resets():
    just_before = datetime(2026, 11, 3, 23, 59, tzinfo=PT)
    just_after = just_before + timedelta(minutes=2)

    assert quota_day(just_before) != quota_day(just_after)


def test_city_and_category_lists_are_sane():
    assert len(CITIES) == len(set(CITIES)) >= 90
    assert len(CATEGORIES) == 7


def test_quota_is_shared_across_output_files_but_progress_is_not(tmp_path):
    first = export(tmp_path, FakePlaces(), output=tmp_path / "one.csv", daily_limit=1)
    second = export(tmp_path, FakePlaces(), output=tmp_path / "two.csv", daily_limit=1)

    assert first.calls_made == 1
    assert (second.calls_made, second.stopped_reason) == (0, "daily quota reached")
    assert (tmp_path / "one.progress.json").exists()
    assert not (tmp_path / "two.csv").read_text(encoding="utf-8").strip().count("place-")
