"""Manage user role ability with security constraints."""

from __future__ import annotations

from backend.core.errors import ValidationError
from backend.providers.admin_dtos import AdminUserListItemDTO, UpdateRoleDTO
from backend.providers.admin_user_provider import AdminUserProvider


def manage_user_role(
    actor_id: str,
    target_id: str,
    dto: UpdateRoleDTO,
    admin_users: AdminUserProvider,
) -> AdminUserListItemDTO:
    """Update a user's role with security constraints.

    Rules:
    - Actor cannot modify their own role (prevents lockout).
    - Cannot demote the last admin to user.
    """
    if actor_id == target_id:
        raise ValidationError("Cannot modify your own role")

    # Check: if demoting from admin to user, ensure not the last admin
    target = admin_users.get_user_detail(target_id)
    if target is None:
        raise ValidationError("User not found")

    if target.role == "admin" and dto.role == "user":
        admin_count = admin_users.count_admin_users()
        if admin_count <= 1:
            raise ValidationError("Cannot demote the last admin user")

    updated = admin_users.update_user_role(target_id, dto)
    if updated is None:
        raise ValidationError("Failed to update user role")
    return updated
