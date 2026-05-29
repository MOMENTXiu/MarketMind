"""Tests for issue_auth_tokens ability atom."""

from backend.abilities.auth.issue_auth_tokens import issue_access_token, issue_auth_token_pair
from tests.fakes.auth_providers import FakeAuthTokenProvider


def test_issue_access_token_returns_string():
    token_provider = FakeAuthTokenProvider()
    token = issue_access_token("user-1", "test@example.com", "Test", token_provider)
    assert isinstance(token, str)
    assert len(token) > 0


def test_issue_auth_token_pair_structure():
    token_provider = FakeAuthTokenProvider()
    pair = issue_auth_token_pair("user-1", "test@example.com", "Test", token_provider)
    assert pair.access_token
    assert pair.token_type == "bearer"


def test_issued_token_can_be_verified():
    token_provider = FakeAuthTokenProvider()
    token = issue_access_token("user-1", "test@example.com", "Test", token_provider)
    claims = token_provider.verify_access_token(token)
    assert claims.sub == "user-1"
    assert claims.email == "test@example.com"
    assert claims.display_name == "Test"
