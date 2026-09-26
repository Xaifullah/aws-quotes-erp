from abc import ABC, abstractmethod
from typing import Any


class ObjectReader(ABC):
    @abstractmethod
    def read(self, key: str) -> list[dict[str, Any]]:
        """Read and deserialize the object at `key`."""


class ObjectWriter(ABC):
    @abstractmethod
    def write(self, key: str, records: list[dict[str, Any]]) -> str:
        """Serialize and write `records`, returning the key written to."""


class DataCleaner(ABC):
    @abstractmethod
    def clean(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return a normalized copy of `records`."""
