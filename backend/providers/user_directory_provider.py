"""User directory provider interface for registration, lookup, and profile updates."""

from typing import Protocol

from backend.providers.auth_dtos import UserIdentityDTO, UserRegistrationInputDTO


class UserDirectoryProvider(Protocol):
    def create_user(self, input_dto: UserRegistrationInputDTO) -> UserIdentityDTO:
        """Create a new user with normalized email and hashed password."""

    def find_user_by_email(self, email: str) -> UserIdentityDTO | None:
        """Find a user by normalized email address."""

    def find_user_by_id(self, user_id: str) -> UserIdentityDTO | None:
        """Find a user by unique id."""

    def update_user_status(self, user_id: str, status: str) -> UserIdentityDTO | None:
        """Update user status (e.g. active, disabled)."""

    def update_last_login(self, user_id: str) -> UserIdentityDTO | None:
        """Update last login timestamp."""
