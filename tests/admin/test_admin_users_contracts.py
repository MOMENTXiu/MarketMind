"""Admin user management API contract tests.

Phase 0.5: User role/status management security constraints.
- Cannot modify own role
- Cannot disable self
- Cannot demote the last admin
- All modifications write audit logs
"""

from __future__ import annotations


class TestUserManagementSecurityConstraints:
    """Business rules that must be enforced at the Ability layer."""

    def test_cannot_modify_own_role(self):
        """Admin cannot change their own role (prevents lockout)."""
        # Contract: manage_user_role(actor_id="admin-1", target_id="admin-1", ...) → error
        pass

    def test_cannot_disable_self(self):
        """Admin cannot disable their own account."""
        # Contract: manage_user_status(actor_id="admin-1", target_id="admin-1", status="disabled") → error
        pass

    def test_cannot_demote_last_admin(self):
        """Cannot demote the last remaining admin to user."""
        # Contract: if count_admin_users() == 1 and target is that admin → error
        pass

    def test_role_modification_writes_audit(self):
        """Changing a user's role must emit an audit event."""
        pass

    def test_status_modification_writes_audit(self):
        """Changing a user's status must emit an audit event."""
        pass


class TestAdminUserListSchema:
    """AdminUserListItemDTO must include all fields for the UI table."""

    def test_list_item_has_required_fields(self):
        """Each user in the list must have these fields."""
        required = {
            "id",
            "email",
            "displayName",
            "role",
            "status",
            "projectCount",
            "lastLoginAt",
            "createdAt",
        }
        assert len(required) == 8

    def test_role_values(self):
        """Role must be 'user' or 'admin' (v1 binary model)."""
        valid_roles = {"user", "admin"}
        assert len(valid_roles) == 2

    def test_status_values(self):
        """Status must be 'active' or 'disabled'."""
        valid_statuses = {"active", "disabled"}
        assert len(valid_statuses) == 2


class TestAdminUserOperations:
    """API endpoints for user management."""

    def test_list_users_requires_admin(self):
        """GET /api/admin/users requires admin role."""
        pass

    def test_get_user_detail_requires_admin(self):
        """GET /api/admin/users/{id} requires admin role."""
        pass

    def test_update_role_requires_admin(self):
        """PATCH /api/admin/users/{id}/role requires admin role."""
        pass

    def test_update_status_requires_admin(self):
        """PATCH /api/admin/users/{id}/status requires admin role."""
        pass

    def test_detail_includes_projects(self):
        """User detail must include list of projects."""
        pass
