"""List admin users ability."""

from __future__ import annotations

from backend.providers.admin_dtos import AdminUserListItemDTO
from backend.providers.admin_user_provider import AdminUserProvider


def list_admin_users(
    admin_users: AdminUserProvider,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AdminUserListItemDTO]:
    """List users with optional search filter."""
    return admin_users.list_users(search=search, offset=offset, limit=limit)
