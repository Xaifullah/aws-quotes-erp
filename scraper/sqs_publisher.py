import json
from datetime import datetime, timezone
from typing import Any

import boto3

from scraper.interfaces import RecordPublisher

# SQS caps a batch at 10 entries and a message at 256 KB. ~25 quotes per message
# keeps each body around 10 KB, well under the limit.
_MAX_BATCH_ENTRIES = 10
_DEFAULT_CHUNK_SIZE = 25


class SqsRecordPublisher(RecordPublisher):
    def __init__(self, queue_url: str, source: str, chunk_size: int = _DEFAULT_CHUNK_SIZE, client=None):
        self._queue_url = queue_url
        self._source = source
        self._chunk_size = chunk_size
        self._client = client or boto3.client("sqs")

    def publish(self, records: list[dict[str, Any]], run_id: str) -> int:
        scraped_at = datetime.now(timezone.utc).isoformat()
        chunks = [records[i : i + self._chunk_size] for i in range(0, len(records), self._chunk_size)]
        entries = [
            {
                "Id": str(index),
                "MessageBody": json.dumps(
                    {
                        "run_id": run_id,
                        "source": self._source,
                        "scraped_at": scraped_at,
                        "records": chunk,
                    },
                    ensure_ascii=False,
                ),
            }
            for index, chunk in enumerate(chunks)
        ]

        for start in range(0, len(entries), _MAX_BATCH_ENTRIES):
            self._send_batch(entries[start : start + _MAX_BATCH_ENTRIES])
        return len(entries)

    def _send_batch(self, entries: list[dict[str, str]]) -> None:
        response = self._client.send_message_batch(QueueUrl=self._queue_url, Entries=entries)
        failed_ids = {failure["Id"] for failure in response.get("Failed", [])}
        if not failed_ids:
            return

        # One retry for entries SQS rejected transiently; anything still failing is fatal.
        retry = [entry for entry in entries if entry["Id"] in failed_ids]
        response = self._client.send_message_batch(QueueUrl=self._queue_url, Entries=retry)
        if response.get("Failed"):
            raise RuntimeError(f"SQS rejected {len(response['Failed'])} message(s): {response['Failed']}")
