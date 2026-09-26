import logging
import os

from scraper.quotes_scraper import QuotesToScrapeScraper
from scraper.s3_storage import S3RawStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    bucket = os.environ["RAW_BUCKET"]
    scraper = QuotesToScrapeScraper()
    storage = S3RawStorage(bucket=bucket)

    records = scraper.scrape()
    key = storage.save(records)
    logger.info("Wrote %d records to s3://%s/%s", len(records), bucket, key)


if __name__ == "__main__":
    main()
