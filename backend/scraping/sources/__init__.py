from scraping.sources.base import Source
from scraping.sources.sebi_ria import SebiRiaSource

SOURCES: dict[str, type[Source]] = {
    SebiRiaSource.definition.key: SebiRiaSource,
}


def get_source(key: str) -> Source:
    try:
        return SOURCES[key]()
    except KeyError:
        raise KeyError(f"Unknown source {key!r}. Available: {', '.join(sorted(SOURCES))}")
