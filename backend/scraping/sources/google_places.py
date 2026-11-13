import csv
import logging
import re
from pathlib import Path
from typing import AsyncIterator

from scraping.http import PoliteClient
from scraping.normalize import collapse_whitespace
from scraping.types import (
    FetchedPage,
    ParseError,
    ProfessionalKind,
    ProfessionType,
    ScrapedRegistration,
    SourceDefinition,
)

LISTING_URL = "https://www.google.com/maps"
PLACEHOLDER_NAME = "Google Maps listing"

CATEGORY_TYPES = {
    "chartered_accountant": ProfessionType.CHARTERED_ACCOUNTANT,
    "tax_consultant": ProfessionType.TAX_CONSULTANT,
    "financial_planner": ProfessionType.LISTED_FINANCIAL_PLANNER,
    "wealth_manager": ProfessionType.WEALTH_MANAGER,
    "investment_advisor": ProfessionType.LISTED_INVESTMENT_ADVISOR,
    "insurance_advisor": ProfessionType.INSURANCE_ADVISOR,
    "estate_planner": ProfessionType.ESTATE_PLANNER,
}
NOISE_NAME_PATTERN = re.compile(
    r"\b(academy|classes|class|coaching|institute|institution|training|trainings|software|tally|"
    r"courses|course|college|school|students?|stationery|printing|xerox|computers?|cyber|cafe)\b",
    re.IGNORECASE,
)
IRRELEVANT_TYPES = {
    "school",
    "university",
    "secondary_school",
    "primary_school",
    "store",
    "electronics_store",
    "book_store",
    "restaurant",
    "cafe",
    "lodging",
    "hospital",
    "doctor",
    "gym",
    "real_estate_agency",
}

logger = logging.getLogger("scraping.google_places")

DEFINITION = SourceDefinition(
    key="google_places",
    name="Google Maps business listings",
    regulator="Google Maps",
    default_profession_type=ProfessionType.CHARTERED_ACCOUNTANT,
    base_url=LISTING_URL,
    verification_level="unverified",
)

REJECTED_COLUMNS = ["reason", "place_id", "name", "category", "searched_city", "address", "types"]


def rejection_reason(row: dict) -> str | None:
    if (row.get("business_status") or "").upper() == "CLOSED_PERMANENTLY":
        return "permanently closed"
    name = row.get("name") or ""
    if NOISE_NAME_PATTERN.search(name):
        return "name looks like a school, software or shop"
    types = {t for t in (row.get("types") or "").split(";") if t}
    if types & IRRELEVANT_TYPES:
        return f"irrelevant place type: {sorted(types & IRRELEVANT_TYPES)[0]}"
    return None


def to_registration(row: dict) -> ScrapedRegistration:
    place_id = collapse_whitespace(row.get("place_id")) or ""
    if not place_id:
        raise ParseError("Row without a place id")
    category = (row.get("category") or "").strip()
    profession_type = CATEGORY_TYPES.get(category)
    if profession_type is None:
        raise ParseError(f"Unknown category {category!r} for {place_id}")
    searched_city = collapse_whitespace(row.get("searched_city"))
    return ScrapedRegistration(
        registration_number=f"GP-{place_id}",
        name=PLACEHOLDER_NAME,
        kind=ProfessionalKind.FIRM,
        profession_type=profession_type,
        valid_from=None,
        valid_until=None,
        validity_raw=None,
        city=searched_city,
        state=None,
        pincode=None,
        address_raw=None,
        email=None,
        phone=None,
        contact_person=None,
        source_url=collapse_whitespace(row.get("google_maps_url")) or LISTING_URL,
        attributes={"google_place_id": place_id},
    )


def read_csv(path: Path) -> tuple[list[ScrapedRegistration], list[dict], int]:
    records: list[ScrapedRegistration] = []
    rejected: list[dict] = []
    parse_errors = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            reason = rejection_reason(row)
            if reason:
                rejected.append({**{c: row.get(c, "") for c in REJECTED_COLUMNS if c != "reason"}, "reason": reason})
                continue
            try:
                records.append(to_registration(row))
            except ParseError as exc:
                logger.warning("skipping unparseable row: %s", exc)
                parse_errors += 1
    return records, rejected, parse_errors


def write_rejected(path: Path, rejected: list[dict]) -> Path:
    target = path.with_name(path.stem + ".rejected.csv")
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REJECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rejected)
    return target


class GooglePlacesCsvSource:
    definition = DEFINITION
    allows_delisting = False
    batch_size = 500

    def __init__(self, path: Path):
        self.path = path
        self.rejected_count = 0

    async def fetch_pages(self, client: PoliteClient | None = None) -> AsyncIterator[FetchedPage]:
        records, rejected, parse_errors = read_csv(self.path)
        self.rejected_count = len(rejected)
        if rejected:
            write_rejected(self.path, rejected)
        total = len(records)
        if not records:
            yield FetchedPage(records=[], parse_errors=parse_errors, expected_total=0)
            return
        for start in range(0, total, self.batch_size):
            yield FetchedPage(
                records=records[start : start + self.batch_size],
                parse_errors=parse_errors if start == 0 else 0,
                expected_total=total,
            )
