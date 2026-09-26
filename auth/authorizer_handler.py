import os
from typing import Any, Optional

from auth.jwt_token_service import InvalidTokenError, JwtTokenService
from auth.ssm_secret_provider import SsmSecretProvider

SECRET_PARAMETER_NAME = os.environ["JWT_SECRET_PARAMETER"]

# Constructed once per warm Lambda container so the JWT secret is fetched from SSM
# once per container, not on every single authorization check.
_token_service = JwtTokenService(SsmSecretProvider(SECRET_PARAMETER_NAME))


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    token = _extract_token(event)

    if not token:
        return {"isAuthorized": False}

    try:
        username = _token_service.verify(token)
    except InvalidTokenError:
        return {"isAuthorized": False}

    return {"isAuthorized": True, "context": {"username": username}}


def _extract_token(event: dict[str, Any]) -> Optional[str]:
    headers = event.get("headers", {})
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header[len("Bearer "):]
