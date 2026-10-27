import json
import logging
import re
from datetime import date, datetime
from typing import AsyncIterator
from urllib.parse import urlencode

from scraping.http import PoliteClient
from scraping.normalize import classify_kind, collapse_whitespace, parse_address
from scraping.types import (
    FetchedPage,
    ParseError,
    ProfessionType,
    ScrapedRegistration,
    ScrapeHttpError,
    SourceDefinition,
)

LISTING_URL = "https://www.amfiindia.com/locate-distributor"
API_URL = "https://www.amfiindia.com/api/distributor-agent"
PAGE_SIZE = 50
ARN_PATTERN = re.compile(r"^\d{1,7}$")
CITY_ENTRY_PATTERN = re.compile(r'\{"City":"((?:[^"\\]|\\.)*)"\}')
PINCODE_PATTERN = re.compile(r"^\d{6}$")

PINCODE_PREFIX_STATES = {
    "11": "Delhi",
    "12": "Haryana",
    "13": "Haryana",
    "14": "Punjab",
    "15": "Punjab",
    "30": "Rajasthan",
    "31": "Rajasthan",
    "32": "Rajasthan",
    "33": "Rajasthan",
    "34": "Rajasthan",
    "36": "Gujarat",
    "37": "Gujarat",
    "38": "Gujarat",
    "41": "Maharashtra",
    "42": "Maharashtra",
    "43": "Maharashtra",
    "44": "Maharashtra",
    "400": "Maharashtra",
    "401": "Maharashtra",
    "402": "Maharashtra",
    "403": "Goa",
    "45": "Madhya Pradesh",
    "46": "Madhya Pradesh",
    "47": "Madhya Pradesh",
    "48": "Madhya Pradesh",
    "56": "Karnataka",
    "57": "Karnataka",
    "58": "Karnataka",
    "59": "Karnataka",
    "67": "Kerala",
    "68": "Kerala",
    "69": "Kerala",
    "68255": "Lakshadweep",
    "70": "West Bengal",
    "71": "West Bengal",
    "72": "West Bengal",
}

logger = logging.getLogger("scraping.amfi_arn")

DEFINITION = SourceDefinition(
    key="amfi_arn",
    name="AMFI Registered Mutual Fund Distributors",
    regulator="AMFI",
    default_profession_type=ProfessionType.MF_DISTRIBUTOR,
    base_url=LISTING_URL,
)


def parse_city_list(html: str) -> list[str]:
    unescaped = html.replace('\\"', '"').replace("\\\\", "\\")
    marker = unescaped.find('"initialCities"')
    if marker == -1:
        return []
    end = unescaped.find('"initialPincodes"', marker)
    section = unescaped[marker : end if end != -1 else None]
    cities: dict[str, str] = {}
    for match in CITY_ENTRY_PATTERN.finditer(section):
        try:
            name = collapse_whitespace(json.loads(f'"{match.group(1)}"'))
        except ValueError:
            name = collapse_whitespace(match.group(1))
        if name:
            cities.setdefault(name.casefold(), name)
    return list(cities.values())


def _parse_iso_date(value: str | None, label: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ParseError(f"Unrecognised {label}: {value!r}") from exc


def _clean(value) -> str | None:
    return collapse_whitespace(value) if isinstance(value, str) else None


def state_from_pincode(pincode: str | None) -> str | None:
    if not pincode or not PINCODE_PATTERN.match(pincode):
        return None
    for length in range(len(pincode), 1, -1):
        state = PINCODE_PREFIX_STATES.get(pincode[:length])
        if state:
            return state
    return None


def to_registration(row: dict) -> ScrapedRegistration:
    arn = _clean(row.get("ARN")) or ""
    if not ARN_PATTERN.match(arn):
        raise ParseError(f"Invalid ARN: {arn!r}")
    registration_number = f"ARN-{arn}"
    name = _clean(row.get("ARNHolderName"))
    if not name:
        raise ParseError(f"Missing name for {registration_number}")
    try:
        valid_from = _parse_iso_date(row.get("ARNValidFrom"), "ARNValidFrom")
        valid_until = _parse_iso_date(row.get("ARNValidTill"), "ARNValidTill")
    except ParseError as exc:
        raise ParseError(f"{registration_number}: {exc}") from exc
    if valid_from and valid_until and valid_until < valid_from:
        raise ParseError(f"{registration_number}: validity ends before it starts")

    address = _clean(row.get("Address"))
    pin = _clean(row.get("Pin"))
    pincode = pin if pin and PINCODE_PATTERN.match(pin) else None
    address_city, address_state, address_pincode = parse_address(address)
    city = _clean(row.get("City")) or address_city
    state = address_state or state_from_pincode(pincode or address_pincode)
    office = _clean(row.get("TelephoneNumber_O"))
    residence = _clean(row.get("TelephoneNumber_R"))
    email = _clean(row.get("Email"))
    validity_raw = " - ".join(
        part for part in (row.get("ARNValidFrom"), row.get("ARNValidTill")) if part
    ) or None

    attributes = {
        key: value
        for key, value in {
            "euin": _clean(row.get("EUIN")),
            "kyd_compliant": _clean(row.get("KYDCompliant")),
            "residence_phone": residence if office and residence != office else None,
            "sif_valid_from": _clean(row.get("SIF_Validity_From")),
            "sif_valid_till": _clean(row.get("SIF_Validity_to")),
            "state_inferred_from_pincode": True if state and not address_state else None,
        }.items()
        if value
    }
    return ScrapedRegistration(
        registration_number=registration_number,
        name=name,
        kind=classify_kind(name),
        profession_type=DEFINITION.default_profession_type,
        valid_from=valid_from,
        valid_until=valid_until,
        validity_raw=validity_raw,
        city=city,
        state=state,
        pincode=pincode or address_pincode,
        address_raw=address,
        email=email.lower() if email else None,
        phone=office or residence,
        contact_person=None,
        source_url=LISTING_URL,
        attributes=attributes,
    )


def parse_api_page(payload: dict) -> tuple[FetchedPage, int, int]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ScrapeHttpError(f"Unexpected AMFI response: {str(payload)[:120]}")
    meta = payload.get("meta") or {}
    total = int(meta.get("total") or 0)
    page_count = int(meta.get("pageCount") or 0)
    records: list[ScrapedRegistration] = []
    parse_errors = 0
    for row in payload["data"]:
        try:
            records.append(to_registration(row))
        except ParseError as exc:
            logger.warning("skipping unparseable record: %s", exc)
            parse_errors += 1
    return FetchedPage(records=records, parse_errors=parse_errors), total, page_count


def _city_url(city: str, page: int) -> str:
    query = urlencode(
        {"strOpt": "ALL", "city": city, "search": "", "page": page, "pageSize": PAGE_SIZE}
    )
    return f"{API_URL}?{query}"


class AmfiArnSource:
    definition = DEFINITION

    async def fetch_pages(self, client: PoliteClient) -> AsyncIterator[FetchedPage]:
        listing = await client.get(LISTING_URL)
        cities = parse_city_list(listing.text)
        if not cities:
            raise ScrapeHttpError("AMFI city list not found on the locate-distributor page")
        expected_total = 0
        for city in cities:
            page_number = 1
            page_count = 1
            while page_number <= page_count:
                response = await client.get(_city_url(city, page_number))
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ScrapeHttpError(f"AMFI returned non-JSON for city {city!r}") from exc
                page, total, page_count = parse_api_page(payload)
                if page_number == 1:
                    expected_total += total
                page.expected_total = expected_total
                page.page_size = PAGE_SIZE
                if total or page.records or page.parse_errors:
                    yield page
                page_number += 1
