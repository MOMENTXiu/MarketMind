"""Password hashing provider interface."""

from typing import Protocol


class PasswordHasherProvider(Protocol):
    def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password and return the encoded hash."""

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a stored hash."""
