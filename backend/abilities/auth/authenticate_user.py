"""User credential authentication ability atom."""

from backend.abilities.auth.normalize_email import normalize_email
from backend.core.errors import DisabledUserError, InvalidCredentialsError
from backend.providers.auth_dtos import UserIdentityDTO
from backend.providers.password_hasher_provider import PasswordHasherProvider
from backend.providers.user_directory_provider import UserDirectoryProvider


def authenticate_user(
    email: str,
    password: str,
    user_directory: UserDirectoryProvider,
    password_hasher: PasswordHasherProvider,
) -> UserIdentityDTO:
    normalized = normalize_email(email)
    user = user_directory.find_user_by_email(normalized)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password")
    if not password_hasher.verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")
    if user.status != "active":
        raise DisabledUserError("User account is disabled")
    return user
