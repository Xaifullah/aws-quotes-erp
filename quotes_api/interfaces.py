from abc import ABC, abstractmethod
from typing import Any, Optional


class QuoteRepository(ABC):
    @abstractmethod
    def list_quotes(self) -> list[dict[str, Any]]:
        """Return all processed quote records."""


class PipelineStatusRepository(ABC):
    @abstractmethod
    def get_status(self) -> dict[str, Optional[int] | Optional[str]]:
        """Return object counts and most-recent-modified timestamps for the raw
        and processed prefixes, to surface scrape/processing pipeline health."""
