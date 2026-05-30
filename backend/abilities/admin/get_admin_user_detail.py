"""Get admin user detail ability."""

from __future__ import annotations

from backend.core.errors import NotFoundError
from backend.providers.admin_dtos import AdminUserDetailDTO
from backend.providers.admin_user_provider import AdminUserProvider


def get_admin_user_detail(
    user_id: str,
    admin_users: AdminUserProvider,
) -> AdminUserDetailDTO:
    """Get detailed user information including project list."""
    detail = admin_users.get_user_detail(user_id)
    if detail is None:
        raise NotFoundError(f"User {user_id} not found")
    return detail
