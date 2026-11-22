import logging
import math
import re
from typing import AsyncIterator

from bs4 import BeautifulSoup

from scraping.config import get_scrape_settings
from scraping.http import PoliteClient
from scraping.normalize import (
    classify_kind,
    collapse_whitespace,
    parse_address,
    parse_validity,
)
from scraping.types import (
    FetchedPage,
    ParseError,
    ProfessionType,
    ScrapedRegistration,
    SourceDefinition,
)

LISTING_URL_TEMPLATE = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId={intermediary_id}"
AJAX_URL = "https://www.sebi.gov.in/sebiweb/ajax/other/getintmfpiinfo.jsp"
LISTING_URL = LISTING_URL_TEMPLATE.format(intermediary_id="13")
INTERMEDIARY_ID = "13"
REGISTRATION_NUMBER_PATTERN = re.compile(r"^INA(\d{9}|IFSC\d{5})$")
RESEARCH_ANALYST_NUMBER_PATTERN = re.compile(r"^INH(\d{9}|IFSC\d{5})$")
RECORD_RANGE_PATTERN = re.compile(r"(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+records", re.IGNORECASE)

logger = logging.getLogger("scraping.sebi_ria")

DEFINITION = SourceDefinition(
    key="sebi_ria",
    name="SEBI Registered Investment Advisers",
    regulator="SEBI",
    default_profession_type=ProfessionType.INVESTMENT_ADVISER,
    base_url=LISTING_URL,
)


def _card_fields(card) -> dict[str, str]:
    fields: dict[str, str] = {}
    for view in card.select("div.card-view"):
        title = view.select_one("div.title span")
        value = view.select_one("div.value span")
        if title is None:
            continue
        label = collapse_whitespace(title.get_text())
        text = collapse_whitespace(value.get_text()) if value is not None else None
        if label and text:
            fields[label.lower()] = text
    return fields


def _to_registration(
    fields: dict[str, str],
    definition: SourceDefinition = DEFINITION,
    number_pattern: re.Pattern[str] = REGISTRATION_NUMBER_PATTERN,
    listing_url: str = LISTING_URL,
) -> ScrapedRegistration:
    registration_number = (fields.get("registration no.") or "").upper()
    if not number_pattern.match(registration_number):
        raise ParseError(f"Invalid registration number: {registration_number!r}")
    name = fields.get("name")
    if not name:
        raise ParseError(f"Missing name for {registration_number}")
    validity_raw = fields.get("validity")
    try:
        valid_from, valid_until = parse_validity(validity_raw)
    except ParseError as exc:
        raise ParseError(f"{registration_number}: {exc}") from exc
    address = fields.get("address") or fields.get("correspondence address")
    city, state, pincode = parse_address(address)
    email = fields.get("e-mail")
    attributes = {
        key: value
        for key, value in {
            "fax": fields.get("fax no."),
            "correspondence_address": fields.get("correspondence address"),
        }.items()
        if value
    }
    return ScrapedRegistration(
        registration_number=registration_number,
        name=name,
        kind=classify_kind(name),
        profession_type=definition.default_profession_type,
        valid_from=valid_from,
        valid_until=valid_until,
        validity_raw=validity_raw,
        city=city,
        state=state,
        pincode=pincode,
        address_raw=address,
        email=email.lower() if email else None,
        phone=fields.get("telephone"),
        contact_person=fields.get("contact person"),
        source_url=listing_url,
        attributes=attributes,
    )


def parse_listing_page(
    html: str,
    definition: SourceDefinition = DEFINITION,
    number_pattern: re.Pattern[str] = REGISTRATION_NUMBER_PATTERN,
    listing_url: str = LISTING_URL,
) -> FetchedPage:
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.select_one("div.pagination_inner")
    expected_total = None
    range_end = None
    range_start = None
    if page_text is not None:
        match = RECORD_RANGE_PATTERN.search(page_text.get_text())
        if match:
            range_start, range_end, expected_total = (int(g) for g in match.groups())

    records: list[ScrapedRegistration] = []
    parse_errors = 0
    for card in soup.select("div.card-table-left"):
        try:
            records.append(_to_registration(_card_fields(card), definition, number_pattern, listing_url))
        except ParseError as exc:
            logger.warning("skipping unparseable record: %s", exc)
            parse_errors += 1
    page = FetchedPage(records=records, parse_errors=parse_errors, expected_total=expected_total)
    page.page_size = (range_end - range_start + 1) if range_start and range_end else None
    return page


class SebiListingSource:
    definition: SourceDefinition = DEFINITION
    intermediary_id = INTERMEDIARY_ID
    number_pattern = REGISTRATION_NUMBER_PATTERN

    @property
    def listing_url(self) -> str:
        return LISTING_URL_TEMPLATE.format(intermediary_id=self.intermediary_id)

    def _parse(self, html: str) -> FetchedPage:
        return parse_listing_page(html, self.definition, self.number_pattern, self.listing_url)

    async def fetch_pages(self, client: PoliteClient) -> AsyncIterator[FetchedPage]:
        max_pages = get_scrape_settings().scrape_max_pages
        first_response = await client.get(self.listing_url)
        first_page = self._parse(first_response.text)
        yield first_page
        if not first_page.expected_total or not first_page.page_size:
            return
        total_pages = min(math.ceil(first_page.expected_total / first_page.page_size), max_pages)
        for page_index in range(1, total_pages):
            response = await client.post(
                AJAX_URL,
                data={
                    "nextValue": "1",
                    "next": "n",
                    "intmId": self.intermediary_id,
                    "contPer": "",
                    "name": "",
                    "regNo": "",
                    "email": "",
                    "location": "",
                    "exchange": "",
                    "affiliate": "",
                    "alp": "",
                    "doDirect": str(page_index),
                    "intmIds": "",
                },
                headers={"Referer": self.listing_url, "X-Requested-With": "XMLHttpRequest"},
            )
            page = self._parse(response.text)
            yield page
            if not page.records and not page.parse_errors:
                return


class SebiRiaSource(SebiListingSource):
    pass
