from typing import Any, Callable

from processing.interfaces import QuoteStore

_UPSERT_RUN = """
    INSERT INTO scrape_runs (run_id, source, started_at, last_message_at, quote_count)
    VALUES (%s, %s, %s, now(), %s)
    ON CONFLICT (run_id) DO UPDATE
       SET last_message_at = now(),
           quote_count     = scrape_runs.quote_count + EXCLUDED.quote_count
"""

_UPSERT_QUOTE = """
    INSERT INTO quotes (id, text, author, tags, processed_at, run_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE
       SET text = EXCLUDED.text,
           author = EXCLUDED.author,
           tags = EXCLUDED.tags,
           processed_at = EXCLUDED.processed_at,
           run_id = EXCLUDED.run_id
"""


class PostgresQuoteStore(QuoteStore):
    def __init__(self, connection_factory: Callable[[], Any]):
        self._connection_factory = connection_factory

    def record_run(self, run_id: str, source: str, started_at: str, quote_count: int) -> None:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(_UPSERT_RUN, (run_id, source, started_at, quote_count))
        finally:
            cursor.close()

    def upsert_quotes(self, records: list[dict[str, Any]], run_id: str) -> int:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.executemany(
                _UPSERT_QUOTE,
                [
                    (r["id"], r["text"], r["author"], r["tags"], r["processed_at"], run_id)
                    for r in records
                ],
            )
        finally:
            cursor.close()
        return len(records)
