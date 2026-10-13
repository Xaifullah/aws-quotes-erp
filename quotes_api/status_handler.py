import json
from typing import Any

from quotes_api.repositories import build_status_repository

_repository = build_status_repository()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    status = _repository.get_status()
    return {"statusCode": 200, "body": json.dumps(status)}
