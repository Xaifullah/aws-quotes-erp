import json
from typing import Any

import boto3

from processing.interfaces import ObjectReader, ObjectWriter


class S3ObjectReader(ObjectReader):
    def __init__(self, bucket: str, client=None):
        self._bucket = bucket
        self._client = client or boto3.client("s3")

    def read(self, key: str) -> list[dict[str, Any]]:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return json.loads(response["Body"].read())


class S3ObjectWriter(ObjectWriter):
    def __init__(self, bucket: str, prefix: str = "processed", source_prefix: str = "raw", client=None):
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._source_prefix = source_prefix.rstrip("/")
        self._client = client or boto3.client("s3")

    def write(self, key: str, records: list[dict[str, Any]]) -> str:
        relative = (
            key[len(self._source_prefix) + 1 :]
            if key.startswith(f"{self._source_prefix}/")
            else key.rsplit("/", 1)[-1]
        )
        target_key = f"{self._prefix}/{relative}"
        body = json.dumps(records, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket, Key=target_key, Body=body, ContentType="application/json"
        )
        return target_key
