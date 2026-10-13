import json
import time
from typing import Any

from quotes_api.repositories import build_quote_repository

_CACHE_TTL_SECONDS = 60

_repository = build_quote_repository()

# Warm-container cache: avoids re-querying the backing store on every request when
# the same Lambda execution environment handles repeated calls.
_cache: dict[str, Any] = {"quotes": None, "fetched_at": 0.0}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    now = time.time()
    if _cache["quotes"] is None or now - _cache["fetched_at"] > _CACHE_TTL_SECONDS:
        _cache["quotes"] = _repository.list_quotes()
        _cache["fetched_at"] = now

    return {"statusCode": 200, "body": json.dumps({"quotes": _cache["quotes"]})}
