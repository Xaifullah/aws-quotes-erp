from datetime import datetime, timedelta, timezone

import jwt

from auth.interfaces import SecretProvider, TokenService

_ALGORITHM = "HS256"
_EXPIRY = timedelta(hours=1)


class InvalidTokenError(Exception):
    pass


class JwtTokenService(TokenService):
    def __init__(self, secret_provider: SecretProvider):
        self._secret_provider = secret_provider

    def issue(self, username: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {"sub": username, "iat": now, "exp": now + _EXPIRY}
        return jwt.encode(payload, self._secret_provider.get_secret(), algorithm=_ALGORITHM)

    def verify(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self._secret_provider.get_secret(), algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        return payload["sub"]
