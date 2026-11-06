from typing import AsyncIterator, Protocol

from scraping.http import PoliteClient
from scraping.types import FetchedPage, SourceDefinition


class Source(Protocol):
    definition: SourceDefinition

    def fetch_pages(self, client: PoliteClient) -> AsyncIterator[FetchedPage]: ...
