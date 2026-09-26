import json
import os
from typing import Any

from auth.bcrypt_hasher import BcryptPasswordHasher, PasswordTooLongError
from auth.dynamodb_user_repository import DynamoDBUserRepository, UsernameAlreadyExistsError

TABLE_NAME = os.environ["USERS_TABLE"]

# Constructed once per warm Lambda container and reused across invocations.
_hasher = BcryptPasswordHasher()
_repository = DynamoDBUserRepository(table_name=TABLE_NAME)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = json.loads(event.get("body") or "{}")
    username = body.get("username", "").strip().lower()
    password = body.get("password", "")

    if not username or not password:
        return _response(400, {"error": "username and password are required"})

    try:
        password_hash = _hasher.hash(password)
    except PasswordTooLongError:
        return _response(400, {"error": "password is too long"})

    try:
        _repository.create(username, password_hash)
    except UsernameAlreadyExistsError:
        return _response(409, {"error": "username already exists"})

    return _response(201, {"username": username})


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}
