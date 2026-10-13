import json
import logging
from typing import Any

from db.connection import get_connection, reset_connection
from processing.postgres_quote_store import PostgresQuoteStore
from processing.quote_cleaner import QuoteCleaner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_store = PostgresQuoteStore(connection_factory=get_connection)
_cleaner = QuoteCleaner()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Partial batch response (requires ReportBatchItemFailures on the event source
    # mapping): only failed messages go back to the queue, and after
    # maxReceiveCount attempts SQS moves them to the DLQ.
    failures = []
    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            written = _process_message(json.loads(record["body"]))
            logger.info("Message %s: upserted %d quotes", message_id, written)
        except Exception:
            logger.exception("Message %s failed", message_id)
            failures.append({"itemIdentifier": message_id})
            reset_connection()

    return {"batchItemFailures": failures}


def _process_message(message: dict[str, Any]) -> int:
    run_id = message["run_id"]
    cleaned = _cleaner.clean(message["records"])

    connection = get_connection()
    try:
        # Run row first: quotes.run_id references scrape_runs.
        _store.record_run(run_id, message.get("source", "unknown"), message["scraped_at"], len(cleaned))
        written = _store.upsert_quotes(cleaned, run_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return written
