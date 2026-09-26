import json
import os
import time
from typing import Any

from quotes_api.s3_quote_repository import S3QuoteRepository

BUCKET_NAME = os.environ["QUOTES_BUCKET"]
_CACHE_TTL_SECONDS = 60

# Warm-container cache: avoids re-fetching and re-parsing every processed/ object on
# every request when the same Lambda execution environment handles repeated calls.
_cache: dict[str, Any] = {"quotes": None, "fetched_at": 0.0}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    now = time.time()
    if _cache["quotes"] is None or now - _cache["fetched_at"] > _CACHE_TTL_SECONDS:
        repository = S3QuoteRepository(bucket=BUCKET_NAME)
        _cache["quotes"] = repository.list_quotes()
        _cache["fetched_at"] = now

    return {"statusCode": 200, "body": json.dumps({"quotes": _cache["quotes"]})}
