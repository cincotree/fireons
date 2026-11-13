from scraping.sources.base import Source
from scraping.sources.fee_only_india import FeeOnlyIndiaSource
from scraping.sources.fpsb_cfp import FpsbCfpSource
from scraping.sources.sebi_research_analyst import SebiResearchAnalystSource
from scraping.sources.sebi_ria import SebiRiaSource

SOURCES: dict[str, type[Source]] = {
    FeeOnlyIndiaSource.definition.key: FeeOnlyIndiaSource,
    FpsbCfpSource.definition.key: FpsbCfpSource,
    SebiResearchAnalystSource.definition.key: SebiResearchAnalystSource,
    SebiRiaSource.definition.key: SebiRiaSource,
}


def get_source(key: str) -> Source:
    try:
        return SOURCES[key]()
    except KeyError:
        raise KeyError(f"Unknown source {key!r}. Available: {', '.join(sorted(SOURCES))}")
