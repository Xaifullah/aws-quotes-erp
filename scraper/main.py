import logging
import os
import uuid

from scraper.quotes_scraper import QuotesToScrapeScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    output = os.environ.get("SCRAPER_OUTPUT", "sqs").lower()
    records = QuotesToScrapeScraper().scrape()

    if output == "sqs":
        from scraper.sqs_publisher import SqsRecordPublisher

        run_id = str(uuid.uuid4())
        publisher = SqsRecordPublisher(queue_url=os.environ["QUEUE_URL"], source="ec2")
        messages = publisher.publish(records, run_id=run_id)
        logger.info("Run %s: published %d records in %d SQS messages", run_id, len(records), messages)
    elif output == "s3":
        # Legacy path (pre-phase-6): raw JSON to S3, picked up by the quotes-processing Lambda.
        from scraper.s3_storage import S3RawStorage

        bucket = os.environ["RAW_BUCKET"]
        key = S3RawStorage(bucket=bucket).save(records)
        logger.info("Wrote %d records to s3://%s/%s", len(records), bucket, key)
    else:
        raise SystemExit(f"Unknown SCRAPER_OUTPUT={output!r}; expected 'sqs' or 's3'")


if __name__ == "__main__":
    main()
