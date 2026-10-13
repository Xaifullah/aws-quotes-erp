from abc import ABC, abstractmethod
from typing import Any


class Scraper(ABC):
    @abstractmethod
    def scrape(self) -> list[dict[str, Any]]:
        """Return a list of scraped records."""


class RawStorage(ABC):
    @abstractmethod
    def save(self, records: list[dict[str, Any]]) -> str:
        """Persist records, returning an identifier (e.g. object key) for what was written."""


class RecordPublisher(ABC):
    @abstractmethod
    def publish(self, records: list[dict[str, Any]], run_id: str) -> int:
        """Publish records for downstream processing, returning the number of messages sent."""
