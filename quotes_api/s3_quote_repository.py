import json
from typing import Any

import boto3

from quotes_api.interfaces import QuoteRepository


class S3QuoteRepository(QuoteRepository):
    def __init__(self, bucket: str, prefix: str = "processed", client=None):
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._client = client or boto3.client("s3")

    def list_quotes(self) -> list[dict[str, Any]]:
        quotes: list[dict[str, Any]] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=f"{self._prefix}/"):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith("/") or obj["Size"] == 0:
                    continue
                response = self._client.get_object(Bucket=self._bucket, Key=obj["Key"])
                quotes.extend(json.loads(response["Body"].read()))
        return quotes
