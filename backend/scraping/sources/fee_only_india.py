import logging
import re
from typing import AsyncIterator
from urllib.parse import urlparse

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

LISTING_URL = "https://www.feeonlyindia.com/list-of-fee-only-planners"
NOTE_PATTERN = re.compile(r"\(\s*\*\s*([^)]*)\)")
LANGUAGES_PATTERN = re.compile(r"^\(\s*([^)]+?)\s*\)$")

logger = logging.getLogger("scraping.fee_only_india")

DEFINITION = SourceDefinition(
    key="fee_only_india",
    name="Fee-Only India Member Planners",
    regulator="Fee-Only India",
    default_profession_type=ProfessionType.FEE_ONLY_PLANNER,
    base_url=LISTING_URL,
)


def registration_number_for(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"FOI-{slug}"


def clean_website(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    path = parsed.path if parsed.path not in {"", "/"} else "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _text(node) -> str | None:
    return collapse_whitespace(node.get_text(" ")) if node is not None else None


def _to_registration(item) -> ScrapedRegistration:
    name = _text(item.find("h4"))
    if not name:
        raise ParseError("Planner card without a name")
    firm_line = _text(item.find("h6"))
    note = None
    firm = firm_line
    if firm_line:
        note_match = NOTE_PATTERN.search(firm_line)
        if note_match:
            note = collapse_whitespace(note_match.group(1))
            firm = collapse_whitespace(NOTE_PATTERN.sub("", firm_line))
    anchor = item.find("a", attrs={"aria-label": "Website"})
    website = clean_website(anchor.get("href") if anchor else None)
    languages: list[str] = []
    for paragraph in item.find_all("p"):
        match = LANGUAGES_PATTERN.match(_text(paragraph) or "")
        if match:
            languages = [part.strip() for part in match.group(1).split(",") if part.strip()]
            break
    attributes = {
        key: value
        for key, value in {
            "firm_name": firm,
            "website": website,
            "languages": languages,
            "note": note,
            "membership": "Fee-Only India",
        }.items()
        if value
    }
    return ScrapedRegistration(
        registration_number=registration_number_for(name),
        name=name,
        kind=ProfessionalKind.INDIVIDUAL,
        profession_type=DEFINITION.default_profession_type,
        valid_from=None,
        valid_until=None,
        validity_raw=None,
        city=None,
        state=None,
        pincode=None,
        address_raw=None,
        email=None,
        phone=None,
        contact_person=name,
        source_url=LISTING_URL,
        attributes=attributes,
    )


def parse_listing_page(html: str) -> FetchedPage:
    soup = BeautifulSoup(html, "lxml")
    items = [item for item in soup.select("div.wixui-repeater__item") if item.find("h6")]
    expected_total = len(soup.find_all("a", attrs={"aria-label": "Website"}))
    records: list[ScrapedRegistration] = []
    parse_errors = 0
    for item in items:
        try:
            records.append(_to_registration(item))
        except ParseError as exc:
            logger.warning("skipping unparseable record: %s", exc)
            parse_errors += 1
    return FetchedPage(records=records, parse_errors=parse_errors, expected_total=expected_total)


class FeeOnlyIndiaSource:
    definition = DEFINITION

    async def fetch_pages(self, client: PoliteClient) -> AsyncIterator[FetchedPage]:
        response = await client.get(LISTING_URL)
        page = parse_listing_page(response.text)
        if not page.records and not page.parse_errors:
            raise ScrapeHttpError("Fee-Only India page has no planner cards; layout may have changed")
        yield page
