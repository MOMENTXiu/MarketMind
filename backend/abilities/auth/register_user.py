"""User registration ability atom."""

from backend.abilities.auth.normalize_email import normalize_email
from backend.core.errors import DuplicateEmailError, ValidationError
from backend.providers.auth_dtos import UserIdentityDTO, UserRegistrationInputDTO
from backend.providers.password_hasher_provider import PasswordHasherProvider
from backend.providers.user_directory_provider import UserDirectoryProvider


def register_user(
    input_dto: UserRegistrationInputDTO,
    user_directory: UserDirectoryProvider,
    password_hasher: PasswordHasherProvider,
) -> UserIdentityDTO:
    email = normalize_email(input_dto.email)
    if not email or "@" not in email:
        raise ValidationError("Valid email is required")
    if not input_dto.password or len(input_dto.password) < 6:
        raise ValidationError("Password must be at least 6 characters")

    existing = user_directory.find_user_by_email(email)
    if existing is not None:
        raise DuplicateEmailError(f"User with email {email} already exists")

    hashed = password_hasher.hash_password(input_dto.password)
    return user_directory.create_user(
        UserRegistrationInputDTO(
            email=email,
            password=hashed,
            display_name=input_dto.display_name,
        )
    )
