from typing import Any, Optional

import boto3

from quotes_api.interfaces import PipelineStatusRepository


class S3PipelineStatusRepository(PipelineStatusRepository):
    def __init__(self, bucket: str, raw_prefix: str = "raw", processed_prefix: str = "processed", client=None):
        self._bucket = bucket
        self._raw_prefix = raw_prefix.rstrip("/")
        self._processed_prefix = processed_prefix.rstrip("/")
        self._client = client or boto3.client("s3")

    def get_status(self) -> dict[str, Any]:
        raw_count, raw_last_modified = self._summarize_prefix(self._raw_prefix)
        processed_count, processed_last_modified = self._summarize_prefix(self._processed_prefix)

        return {
            "raw_count": raw_count,
            "processed_count": processed_count,
            "last_scraped_at": raw_last_modified,
            "last_processed_at": processed_last_modified,
        }

    def _summarize_prefix(self, prefix: str) -> tuple[int, Optional[str]]:
        count = 0
        latest = None
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=f"{prefix}/"):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith("/") or obj["Size"] == 0:
                    continue
                count += 1
                if latest is None or obj["LastModified"] > latest:
                    latest = obj["LastModified"]
        return count, latest.isoformat() if latest else None
