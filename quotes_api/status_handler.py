import json
import os
from typing import Any

from quotes_api.s3_pipeline_status_repository import S3PipelineStatusRepository

BUCKET_NAME = os.environ["QUOTES_BUCKET"]

_repository = S3PipelineStatusRepository(bucket=BUCKET_NAME)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    status = _repository.get_status()
    return {"statusCode": 200, "body": json.dumps(status)}
