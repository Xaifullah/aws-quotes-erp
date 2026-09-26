import bcrypt

from auth.interfaces import PasswordHasher

MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    pass


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise PasswordTooLongError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# A precomputed hash with no corresponding real password, used to keep login's bcrypt
# work constant whether or not the username exists (avoids a user-enumeration timing gap).
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"login-timing-safety-dummy", bcrypt.gensalt()).decode("utf-8")
