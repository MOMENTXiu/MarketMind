"""Tests for issue_sse_ticket ability atom."""

import pytest

from backend.abilities.auth.issue_sse_ticket import issue_sse_ticket
from backend.core.errors import NotFoundError
from backend.providers.auth_dtos import AuthenticatedUserContext
from tests.fakes.auth_providers import FakeSseTicketProvider
from tests.fakes.providers import FakeProjectRepositoryProvider


def test_issue_sse_ticket_success():
    user_ctx = AuthenticatedUserContext(user_id="user-1", email="test@example.com")
    sse = FakeSseTicketProvider()
    ticket = issue_sse_ticket(
        user_ctx, "project", "proj-1", sse,
    )
    assert ticket.ticket
    assert ticket.user_id == "user-1"
    assert ticket.resource_type == "project"
    assert ticket.resource_id == "proj-1"


def test_issue_sse_ticket_with_project_verification():
    user_ctx = AuthenticatedUserContext(user_id="user-1", email="test@example.com")
    repo = FakeProjectRepositoryProvider()
    from backend.models.project import ProjectCreate
    repo.create_project(ProjectCreate(name="Test", owner_user_id="user-1"))
    project_id = list(repo.projects.keys())[0]
    sse = FakeSseTicketProvider()
    ticket = issue_sse_ticket(
        user_ctx, "project", project_id, sse,
        project_repository=repo, project_id=project_id,
    )
    assert ticket.ticket


def test_issue_sse_ticket_project_not_found():
    user_ctx = AuthenticatedUserContext(user_id="user-1", email="test@example.com")
    repo = FakeProjectRepositoryProvider()
    sse = FakeSseTicketProvider()
    with pytest.raises(NotFoundError):
        issue_sse_ticket(
            user_ctx, "project", "nonexistent", sse,
            project_repository=repo, project_id="nonexistent",
        )
