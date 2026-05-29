"""Tests for assert_project_access ability atom."""

import pytest

from backend.abilities.auth.assert_project_access import assert_project_access
from backend.core.errors import NotFoundError
from backend.models.project import ProjectCreate
from backend.providers.auth_dtos import AuthenticatedUserContext
from tests.fakes.providers import FakeProjectRepositoryProvider


def test_assert_project_access_success():
    repo = FakeProjectRepositoryProvider()
    project = repo.create_project(ProjectCreate(name="Test", owner_user_id="user-1"))
    ctx = AuthenticatedUserContext(user_id="user-1", email="test@example.com")
    assert_project_access(project.id, ctx, repo)


def test_assert_project_access_cross_user_returns_not_found():
    repo = FakeProjectRepositoryProvider()
    project = repo.create_project(ProjectCreate(name="Test", owner_user_id="user-1"))
    ctx = AuthenticatedUserContext(user_id="user-2", email="other@example.com")
    with pytest.raises(NotFoundError):
        assert_project_access(project.id, ctx, repo)


def test_assert_project_access_missing_project():
    repo = FakeProjectRepositoryProvider()
    ctx = AuthenticatedUserContext(user_id="user-1", email="test@example.com")
    with pytest.raises(NotFoundError):
        assert_project_access("nonexistent", ctx, repo)
