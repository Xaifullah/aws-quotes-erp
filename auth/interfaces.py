from abc import ABC, abstractmethod
from typing import Any, Optional


class UserRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        """Return the user record for `username`, or None if it doesn't exist."""

    @abstractmethod
    def create(self, username: str, password_hash: str) -> None:
        """Create a new user. Raises if the username already exists."""


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        """Return a salted hash of `password`."""

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """Return True if `password` matches `password_hash`."""


class TokenService(ABC):
    @abstractmethod
    def issue(self, username: str) -> str:
        """Return a signed token for `username`."""

    @abstractmethod
    def verify(self, token: str) -> str:
        """Return the username encoded in `token`, or raise if invalid/expired."""


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self) -> str:
        """Return the current secret value."""
