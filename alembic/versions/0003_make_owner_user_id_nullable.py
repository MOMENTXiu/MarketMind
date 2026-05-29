"""Make projects.owner_user_id nullable."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_make_owner_user_id_nullable"
down_revision: str | None = "0002_users_project_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("projects", "owner_user_id", nullable=True)


def downgrade() -> None:
    op.alter_column("projects", "owner_user_id", nullable=False)
