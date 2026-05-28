"""Tests for authenticate_user ability atom."""

import pytest

from backend.abilities.auth.authenticate_user import authenticate_user
from backend.core.errors import DisabledUserError, InvalidCredentialsError
from backend.providers.auth_dtos import UserRegistrationInputDTO
from tests.fakes.auth_providers import FakePasswordHasherProvider, FakeUserDirectoryProvider


def _register(directory, hasher, email, password):
    return directory.create_user(
        UserRegistrationInputDTO(
            email=email,
            password=hasher.hash_password(password),
            display_name=None,
        )
    )


def test_authenticate_user_success():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    _register(directory, hasher, "test@example.com", "secret")
    result = authenticate_user("test@example.com", "secret", directory, hasher)
    assert result.email == "test@example.com"


def test_authenticate_user_invalid_password():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    _register(directory, hasher, "test@example.com", "secret")
    with pytest.raises(InvalidCredentialsError):
        authenticate_user("test@example.com", "wrong", directory, hasher)


def test_authenticate_user_unknown_email():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    with pytest.raises(InvalidCredentialsError):
        authenticate_user("unknown@example.com", "secret", directory, hasher)


def test_authenticate_user_disabled_account():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    user = _register(directory, hasher, "test@example.com", "secret")
    directory.update_user_status(user.id, "disabled")
    with pytest.raises(DisabledUserError):
        authenticate_user("test@example.com", "secret", directory, hasher)
