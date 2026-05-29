"""Add users, sse_tickets, and project owner_user_id."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0002_users_project_ownership"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_USER_ID = "00000000000000000000000000000000"


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_status", "users", ["status"])

    # 2. Create sse_tickets table
    op.create_table(
        "sse_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_hash", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("stream_type", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sse_tickets_ticket_hash", "sse_tickets", ["ticket_hash"])
    op.create_index("ix_sse_tickets_user_id", "sse_tickets", ["user_id"])

    # 3. Add nullable owner_user_id to projects
    op.add_column(
        "projects",
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
    )

    # 4. Create legacy/system owner user for existing projects
    now = datetime.now(UTC)
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, password_hash, display_name, status, created_at, updated_at)
            VALUES (:id, :email, :password_hash, :display_name, :status, :created_at, :updated_at)
            """
        ).bindparams(
            id=LEGACY_USER_ID,
            email="legacy@system.local",
            password_hash="$2b$12$" + "x" * 53,  # invalid hash placeholder
            display_name="Legacy System Owner",
            status="active",
            created_at=now,
            updated_at=now,
        )
    )

    # 5. Backfill existing projects to legacy owner
    op.execute(
        sa.text(
            "UPDATE projects SET owner_user_id = :owner_id WHERE owner_user_id IS NULL"
        ).bindparams(owner_id=LEGACY_USER_ID)
    )

    # 6. Add FK and indexes
    op.create_foreign_key(
        "fk_projects_owner_user_id",
        "projects",
        "users",
        ["owner_user_id"],
        ["id"],
    )
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"])
    op.create_index("ix_projects_owner_user_id_id", "projects", ["owner_user_id", "id"])
    op.create_index(
        "ix_projects_owner_user_id_updated_at", "projects", ["owner_user_id", "updated_at"]
    )

    # 7. owner_user_id remains nullable to support anonymous projects
    # when AUTH_ENFORCE_ANALYSIS_AUTH=False.


def downgrade() -> None:
    op.drop_index("ix_projects_owner_user_id_updated_at", table_name="projects")
    op.drop_index("ix_projects_owner_user_id_id", table_name="projects")
    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    op.drop_constraint("fk_projects_owner_user_id", "projects", type_="foreignkey")
    op.drop_column("projects", "owner_user_id")

    op.drop_index("ix_sse_tickets_user_id", table_name="sse_tickets")
    op.drop_index("ix_sse_tickets_ticket_hash", table_name="sse_tickets")
    op.drop_table("sse_tickets")

    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
