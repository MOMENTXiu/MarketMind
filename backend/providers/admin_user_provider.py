"""Admin user provider interface.

Separate from UserDirectoryProvider (which handles auth/registration).
This provider handles admin-level user listing, counting, role/status
management.
"""

from __future__ import annotations

from typing import Protocol

from backend.providers.admin_dtos import (
    AdminUserDetailDTO,
    AdminUserListItemDTO,
    UpdateRoleDTO,
    UpdateStatusDTO,
)


class AdminUserProvider(Protocol):
    """Admin-level user management operations."""

    def list_users(
        self, search: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[AdminUserListItemDTO]:
        """List all users with optional search filter."""

    def count_users(self) -> int:
        """Return total number of users."""

    def count_admin_users(self) -> int:
        """Return number of users with role='admin'."""

    def get_user_detail(self, user_id: str) -> AdminUserDetailDTO | None:
        """Get detailed user information including project list."""

    def update_user_role(self, user_id: str, dto: UpdateRoleDTO) -> AdminUserListItemDTO | None:
        """Update a user's role. Returns updated user or None if not found."""

    def update_user_status(self, user_id: str, dto: UpdateStatusDTO) -> AdminUserListItemDTO | None:
        """Enable or disable a user. Returns updated user or None if not found."""
