from typing import Any, Callable

from quotes_api.interfaces import QuoteRepository

_SELECT_QUOTES = "SELECT id, text, author, tags, processed_at FROM quotes ORDER BY author, id"


def _fetch_quotes(connection: Any) -> list[tuple]:
    cursor = connection.cursor()
    try:
        cursor.execute(_SELECT_QUOTES)
        rows = cursor.fetchall()
    finally:
        cursor.close()
    connection.rollback()  # end the read-only transaction so the next call sees fresh data
    return rows


class PostgresQuoteRepository(QuoteRepository):
    def __init__(self, run_query: Callable[[Callable[[Any], Any]], Any]):
        # run_query(operation) supplies a live connection to `operation` —
        # db.connection.run_with_reconnect in production, a stub in tests.
        self._run_query = run_query

    def list_quotes(self) -> list[dict[str, Any]]:
        rows = self._run_query(_fetch_quotes)

        # Same shape the S3 repository returned, so the frontend contract is unchanged.
        return [
            {
                "id": quote_id,
                "text": text,
                "author": author,
                "tags": list(tags or []),
                "processed_at": processed_at.isoformat(),
            }
            for quote_id, text, author, tags, processed_at in rows
        ]
