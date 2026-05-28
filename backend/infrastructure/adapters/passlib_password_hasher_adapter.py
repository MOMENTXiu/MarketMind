"""Passlib-based password hashing adapter."""

from passlib.context import CryptContext

from backend.core.errors import InfrastructureError
from backend.providers.password_hasher_provider import PasswordHasherProvider


class PasslibPasswordHasherAdapter(PasswordHasherProvider):
    def __init__(self, rounds: int = 12) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=rounds)

    def hash_password(self, plain_password: str) -> str:
        try:
            return self._ctx.hash(plain_password)
        except Exception as exc:
            raise InfrastructureError(f"Password hashing failed: {exc}") from exc

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return self._ctx.verify(plain_password, hashed_password)
        except Exception:
            return False
