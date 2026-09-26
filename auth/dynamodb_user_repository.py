from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from auth.interfaces import UserRepository


class UsernameAlreadyExistsError(Exception):
    pass


class DynamoDBUserRepository(UserRepository):
    def __init__(self, table_name: str, resource=None):
        self._table = (resource or boto3.resource("dynamodb")).Table(table_name)

    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        response = self._table.get_item(Key={"username": username})
        return response.get("Item")

    def create(self, username: str, password_hash: str) -> None:
        try:
            self._table.put_item(
                Item={"username": username, "password_hash": password_hash},
                ConditionExpression="attribute_not_exists(username)",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise UsernameAlreadyExistsError(username) from exc
            raise
