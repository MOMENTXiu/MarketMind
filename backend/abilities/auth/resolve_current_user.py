"""Resolve current user from access token ability atom."""

from backend.core.errors import DisabledUserError, NotFoundError
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.auth_token_provider import AuthTokenProvider
from backend.providers.user_directory_provider import UserDirectoryProvider


def resolve_current_user(
    token: str,
    auth_token: AuthTokenProvider,
    user_directory: UserDirectoryProvider,
) -> AuthenticatedUserContext:
    claims = auth_token.verify_access_token(token)
    user = user_directory.find_user_by_id(claims.sub)
    if user is None:
        raise NotFoundError("User not found")
    if user.status != "active":
        raise DisabledUserError("User account is disabled")
    return AuthenticatedUserContext(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )
