from scraping.sources.sebi_ria import (
    LISTING_URL_TEMPLATE,
    RESEARCH_ANALYST_NUMBER_PATTERN,
    SebiListingSource,
)
from scraping.types import ProfessionType, SourceDefinition

INTERMEDIARY_ID = "14"
LISTING_URL = LISTING_URL_TEMPLATE.format(intermediary_id=INTERMEDIARY_ID)

DEFINITION = SourceDefinition(
    key="sebi_research_analyst",
    name="SEBI Registered Research Analysts",
    regulator="SEBI",
    default_profession_type=ProfessionType.RESEARCH_ANALYST,
    base_url=LISTING_URL,
)


class SebiResearchAnalystSource(SebiListingSource):
    definition = DEFINITION
    intermediary_id = INTERMEDIARY_ID
    number_pattern = RESEARCH_ANALYST_NUMBER_PATTERN
