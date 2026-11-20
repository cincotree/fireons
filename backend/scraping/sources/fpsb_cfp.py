import logging
import re
from typing import AsyncIterator

from bs4 import BeautifulSoup

from scraping.http import PoliteClient
from scraping.normalize import collapse_whitespace
from scraping.types import (
    FetchedPage,
    ParseError,
    ProfessionalKind,
    ProfessionType,
    ScrapedRegistration,
    ScrapeHttpError,
    SourceDefinition,
)

LISTING_URL = "https://india.fpsb.org/cfp-certificants-directory/"
FPSB_NUMBER_PATTERN = re.compile(r"^IN\d{4,8}$")

logger = logging.getLogger("scraping.fpsb_cfp")

DEFINITION = SourceDefinition(
    key="fpsb_cfp",
    name="FPSB India CFP Certificants",
    regulator="FPSB India",
    default_profession_type=ProfessionType.CERTIFIED_FINANCIAL_PLANNER,
    base_url=LISTING_URL,
)


def _clean_city(value: str | None) -> str | None:
    city = collapse_whitespace(value)
    return city.title() if city else None


def _to_registration(cells: list[str]) -> ScrapedRegistration:
    if len(cells) < 4:
        raise ParseError(f"Row has {len(cells)} cells")
    number = cells[1].strip().upper()
    if not FPSB_NUMBER_PATTERN.match(number):
        raise ParseError(f"Invalid FPSB number: {number!r}")
    name = collapse_whitespace(cells[2])
    if not name:
        raise ParseError(f"Missing name for {number}")
    return ScrapedRegistration(
        registration_number=number,
        name=name.title() if name.isupper() else name,
        kind=ProfessionalKind.INDIVIDUAL,
        profession_type=DEFINITION.default_profession_type,
        valid_from=None,
        valid_until=None,
        validity_raw=None,
        city=_clean_city(cells[3]),
        state=None,
        pincode=None,
        address_raw=None,
        email=None,
        phone=None,
        contact_person=None,
        source_url=LISTING_URL,
        attributes={"certification": "CFP"},
    )


def parse_listing_page(html: str) -> FetchedPage:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return FetchedPage(records=[])
    records: list[ScrapedRegistration] = []
    parse_errors = 0
    highest_serial = 0
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if not cells:
            continue
        if cells[0].isdigit():
            highest_serial = max(highest_serial, int(cells[0]))
        try:
            records.append(_to_registration(cells))
        except ParseError as exc:
            logger.warning("skipping unparseable record: %s", exc)
            parse_errors += 1
    return FetchedPage(
        records=records, parse_errors=parse_errors, expected_total=highest_serial or None
    )


class FpsbCfpSource:
    definition = DEFINITION

    async def fetch_pages(self, client: PoliteClient) -> AsyncIterator[FetchedPage]:
        response = await client.get(LISTING_URL)
        page = parse_listing_page(response.text)
        if not page.records and not page.parse_errors:
            raise ScrapeHttpError("FPSB directory has no certificant rows; layout may have changed")
        yield page
