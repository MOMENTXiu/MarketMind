"""Resolve current user from bearer token business pipeline."""

from backend.abilities.auth.resolve_current_user import resolve_current_user
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer


class ResolveCurrentUserPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def execute(self, token: str) -> AuthenticatedUserContext:
        if self.providers.auth_token is None or self.providers.user_directory is None:
            raise RuntimeError("Auth providers not configured")
        return resolve_current_user(
            token=token,
            auth_token=self.providers.auth_token,
            user_directory=self.providers.user_directory,
        )
