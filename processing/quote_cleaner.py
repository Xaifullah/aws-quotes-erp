import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from processing.interfaces import DataCleaner

logger = logging.getLogger(__name__)

_WRAPPING_QUOTE_CHARS = "“”\"'"


class QuoteCleaner(DataCleaner):
    def clean(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned = []
        for record in records:
            try:
                cleaned.append(self._clean_one(record))
            except (AttributeError, TypeError):
                logger.warning("Skipping malformed record: %r", record)
        return cleaned

    def _clean_one(self, record: dict[str, Any]) -> dict[str, Any]:
        text = (record.get("text") or "").strip().strip(_WRAPPING_QUOTE_CHARS).strip()
        author = (record.get("author") or "").strip()
        tags = sorted({tag.strip().lower() for tag in (record.get("tags") or []) if tag.strip()})

        return {
            "id": self._make_id(author, text),
            "text": text,
            "author": author,
            "tags": tags,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _make_id(author: str, text: str) -> str:
        digest = hashlib.sha256(f"{author}::{text}".encode("utf-8")).hexdigest()
        return digest[:16]
