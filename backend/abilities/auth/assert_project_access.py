"""Assert project access ability atom."""

from backend.core.errors import NotFoundError
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.project_repository_provider import ProjectRepositoryProvider


def assert_project_access(
    project_id: str,
    user_context: AuthenticatedUserContext,
    project_repository: ProjectRepositoryProvider,
) -> None:
    project = project_repository.get_project(project_id, owner_user_id=user_context.user_id)
    if project is None:
        raise NotFoundError("Project not found")
