from typing import Any, Callable

from quotes_api.interfaces import PipelineStatusRepository

_SELECT_STATUS = """
    SELECT (SELECT count(*) FROM scrape_runs),
           (SELECT count(*) FROM quotes),
           (SELECT max(started_at) FROM scrape_runs),
           (SELECT max(processed_at) FROM quotes)
"""


def _fetch_status(connection: Any) -> tuple:
    cursor = connection.cursor()
    try:
        cursor.execute(_SELECT_STATUS)
        row = cursor.fetchone()
    finally:
        cursor.close()
    connection.rollback()
    return row


class PostgresPipelineStatusRepository(PipelineStatusRepository):
    """Keeps the S3 repository's keys so the frontend contract is unchanged:
    raw_count = scrape runs, processed_count = quotes stored in the database."""

    def __init__(self, run_query: Callable[[Callable[[Any], Any]], Any]):
        self._run_query = run_query

    def get_status(self) -> dict[str, Any]:
        run_count, quote_count, last_scraped, last_processed = self._run_query(_fetch_status)

        return {
            "raw_count": run_count,
            "processed_count": quote_count,
            "last_scraped_at": last_scraped.isoformat() if last_scraped else None,
            "last_processed_at": last_processed.isoformat() if last_processed else None,
        }
