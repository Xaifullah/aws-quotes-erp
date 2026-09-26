import json
from datetime import datetime, timezone
from typing import Any

import boto3

from scraper.interfaces import RawStorage


class S3RawStorage(RawStorage):
    def __init__(self, bucket: str, prefix: str = "raw", client=None):
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._client = client or boto3.client("s3")

    def save(self, records: list[dict[str, Any]]) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"{self._prefix}/{timestamp}.json"
        body = json.dumps(records, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=body, ContentType="application/json"
        )
        return key
