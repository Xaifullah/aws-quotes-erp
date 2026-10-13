import json
import logging
import os
import uuid
from typing import Any

from scraper.quotes_scraper import QuotesToScrapeScraper
from scraper.sqs_publisher import SqsRecordPublisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUEUE_URL = os.environ["QUEUE_URL"]

_publisher = SqsRecordPublisher(queue_url=QUEUE_URL, source="lambda")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    try:
        records = QuotesToScrapeScraper().scrape()
    except Exception:
        logger.exception("Scrape failed for run %s", run_id)
        return {"statusCode": 502, "body": json.dumps({"error": "Scrape of source site failed"})}

    messages = _publisher.publish(records, run_id=run_id)
    logger.info("Run %s: published %d records in %d messages", run_id, len(records), messages)

    return {
        "statusCode": 202,
        "body": json.dumps({"run_id": run_id, "published": len(records), "messages": messages}),
    }
