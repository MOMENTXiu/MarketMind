"""Tests for register_user ability atom."""

import pytest

from backend.abilities.auth.register_user import register_user
from backend.core.errors import DuplicateEmailError, ValidationError
from backend.providers.auth_dtos import UserRegistrationInputDTO
from tests.fakes.auth_providers import FakePasswordHasherProvider, FakeUserDirectoryProvider


def test_register_user_success():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    result = register_user(
        UserRegistrationInputDTO(email="test@example.com", password="password123"),
        directory,
        hasher,
    )
    assert result.email == "test@example.com"
    assert result.status == "active"
    assert result.id


def test_register_user_normalizes_email():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    result = register_user(
        UserRegistrationInputDTO(email="  Test@Example.COM  ", password="password123"),
        directory,
        hasher,
    )
    assert result.email == "test@example.com"


def test_register_user_rejects_duplicate_email():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    register_user(
        UserRegistrationInputDTO(email="test@example.com", password="password123"),
        directory,
        hasher,
    )
    with pytest.raises(DuplicateEmailError):
        register_user(
            UserRegistrationInputDTO(email="test@example.com", password="otherpass"),
            directory,
            hasher,
        )


def test_register_user_rejects_short_password():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    with pytest.raises(ValidationError):
        register_user(
            UserRegistrationInputDTO(email="test@example.com", password="123"),
            directory,
            hasher,
        )


def test_register_user_rejects_invalid_email():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    with pytest.raises(ValidationError):
        register_user(
            UserRegistrationInputDTO(email="not-an-email", password="password123"),
            directory,
            hasher,
        )
