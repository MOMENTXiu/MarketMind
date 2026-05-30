"""Admin user pipeline — list, detail, role/status management with audit."""

from __future__ import annotations

from backend.abilities.admin.get_admin_user_detail import get_admin_user_detail
from backend.abilities.admin.list_admin_users import list_admin_users
from backend.abilities.admin.manage_user_role import manage_user_role
from backend.abilities.admin.manage_user_status import manage_user_status
from backend.providers.admin_dtos import (
    AdminUserDetailDTO,
    AdminUserListItemDTO,
    UpdateRoleDTO,
    UpdateStatusDTO,
)
from backend.providers.container import ProvidersContainer
from backend.providers.telemetry_dtos import AuditEvent


class AdminUserPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self._providers = providers

    def _require_admin_users(self):
        if self._providers.admin_users is None:
            raise RuntimeError("Admin user provider not configured")
        return self._providers.admin_users

    def list_users(
        self, search: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[AdminUserListItemDTO]:
        return list_admin_users(
            self._require_admin_users(), search=search, offset=offset, limit=limit
        )

    def get_user_detail(self, user_id: str) -> AdminUserDetailDTO:
        return get_admin_user_detail(user_id, self._require_admin_users())

    def update_user_role(
        self, actor_id: str, target_id: str, dto: UpdateRoleDTO
    ) -> AdminUserListItemDTO:
        result = manage_user_role(actor_id, target_id, dto, self._require_admin_users())
        self._emit_audit(
            actor_id, "admin.modify_user_role", "user", target_id, metadata={"new_role": dto.role}
        )
        return result

    def update_user_status(
        self, actor_id: str, target_id: str, dto: UpdateStatusDTO
    ) -> AdminUserListItemDTO:
        result = manage_user_status(actor_id, target_id, dto, self._require_admin_users())
        self._emit_audit(
            actor_id,
            "admin.modify_user_status",
            "user",
            target_id,
            metadata={"new_status": dto.status},
        )
        return result

    def _emit_audit(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None,
        metadata: dict | None = None,
    ) -> None:
        telemetry = self._providers.telemetry
        if telemetry is None:
            return
        telemetry.emit_audit(
            AuditEvent(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status="success",
                redaction_summary=metadata or {},
            )
        )
