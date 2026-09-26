import json
import os
from typing import Any

from auth.bcrypt_hasher import DUMMY_PASSWORD_HASH, BcryptPasswordHasher
from auth.dynamodb_user_repository import DynamoDBUserRepository
from auth.jwt_token_service import JwtTokenService
from auth.ssm_secret_provider import SsmSecretProvider

TABLE_NAME = os.environ["USERS_TABLE"]
SECRET_PARAMETER_NAME = os.environ["JWT_SECRET_PARAMETER"]

# Constructed once per warm Lambda container, not per invocation, so the JWT secret
# fetched from SSM is cached and reused across requests instead of re-fetched every time.
_hasher = BcryptPasswordHasher()
_repository = DynamoDBUserRepository(table_name=TABLE_NAME)
_token_service = JwtTokenService(SsmSecretProvider(SECRET_PARAMETER_NAME))


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = json.loads(event.get("body") or "{}")
    username = body.get("username", "").strip().lower()
    password = body.get("password", "")

    if not username or not password:
        return _response(400, {"error": "username and password are required"})

    user = _repository.get_by_username(username)
    # Always run bcrypt, even for an unknown username, so response time doesn't reveal
    # whether the username exists (a real hash-shaped dummy keeps the work identical).
    password_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
    is_valid = _hasher.verify(password, password_hash)

    if not user or not is_valid:
        return _response(401, {"error": "invalid username or password"})

    token = _token_service.issue(username)
    return _response(200, {"token": token})


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}
