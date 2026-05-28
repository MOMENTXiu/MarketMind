"""Tests for resolve_current_user ability atom."""

import pytest

from backend.abilities.auth.resolve_current_user import resolve_current_user
from backend.core.errors import DisabledUserError, ExpiredTokenError, InvalidTokenError, NotFoundError
from backend.providers.auth_dtos import AuthTokenClaimsDTO, UserRegistrationInputDTO
from tests.fakes.auth_providers import FakeAuthTokenProvider, FakeUserDirectoryProvider


def _register(directory, email):
    return directory.create_user(
        UserRegistrationInputDTO(email=email, password="hash", display_name=None)
    )


def test_resolve_current_user_success():
    directory = FakeUserDirectoryProvider()
    token_provider = FakeAuthTokenProvider()
    user = _register(directory, "test@example.com")
    token = token_provider.sign_access_token(
        AuthTokenClaimsDTO(sub=user.id, email=user.email, display_name=user.display_name)
    )
    result = resolve_current_user(token, token_provider, directory)
    assert result.user_id == user.id
    assert result.email == user.email


def test_resolve_current_user_invalid_token():
    directory = FakeUserDirectoryProvider()
    token_provider = FakeAuthTokenProvider()
    with pytest.raises(InvalidTokenError):
        resolve_current_user("bad-token", token_provider, directory)


def test_resolve_current_user_expired_token():
    directory = FakeUserDirectoryProvider()
    token_provider = FakeAuthTokenProvider()
    user = _register(directory, "test@example.com")
    token = token_provider.make_expired_token(
        AuthTokenClaimsDTO(sub=user.id, email=user.email, display_name=None)
    )
    with pytest.raises(ExpiredTokenError):
        resolve_current_user(token, token_provider, directory)


def test_resolve_current_user_user_not_found():
    directory = FakeUserDirectoryProvider()
    token_provider = FakeAuthTokenProvider()
    token = token_provider.sign_access_token(
        AuthTokenClaimsDTO(sub="nonexistent", email="test@example.com", display_name=None)
    )
    with pytest.raises(NotFoundError):
        resolve_current_user(token, token_provider, directory)


def test_resolve_current_user_disabled_user():
    directory = FakeUserDirectoryProvider()
    token_provider = FakeAuthTokenProvider()
    user = _register(directory, "test@example.com")
    directory.update_user_status(user.id, "disabled")
    token = token_provider.sign_access_token(
        AuthTokenClaimsDTO(sub=user.id, email=user.email, display_name=None)
    )
    with pytest.raises(DisabledUserError):
        resolve_current_user(token, token_provider, directory)
