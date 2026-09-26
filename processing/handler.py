import logging
from typing import Any

from processing.quote_cleaner import QuoteCleaner
from processing.s3_objects import S3ObjectReader, S3ObjectWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    processed_keys = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        if key.startswith("processed/"):
            logger.warning("Skipping %s: already under processed/ (loop guard)", key)
            continue

        reader = S3ObjectReader(bucket=bucket)
        writer = S3ObjectWriter(bucket=bucket)
        cleaner = QuoteCleaner()

        raw_records = reader.read(key)
        cleaned_records = cleaner.clean(raw_records)
        target_key = writer.write(key, cleaned_records)

        logger.info("Processed s3://%s/%s -> s3://%s/%s", bucket, key, bucket, target_key)
        processed_keys.append(target_key)

    return {"processed": processed_keys}
