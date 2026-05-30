"""Manage user status (enable/disable) ability with security constraints."""

from __future__ import annotations

from backend.core.errors import ValidationError
from backend.providers.admin_dtos import AdminUserListItemDTO, UpdateStatusDTO
from backend.providers.admin_user_provider import AdminUserProvider


def manage_user_status(
    actor_id: str,
    target_id: str,
    dto: UpdateStatusDTO,
    admin_users: AdminUserProvider,
) -> AdminUserListItemDTO:
    """Enable or disable a user with security constraints.

    Rules:
    - Actor cannot disable themselves.
    """
    if actor_id == target_id:
        raise ValidationError("Cannot modify your own status")

    updated = admin_users.update_user_status(target_id, dto)
    if updated is None:
        raise ValidationError("Failed to update user status")
    return updated
