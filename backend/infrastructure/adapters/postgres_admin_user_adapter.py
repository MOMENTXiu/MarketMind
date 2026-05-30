"""PostgreSQL admin user adapter.

Implements AdminUserProvider for admin-level user management
(listing, counting, role/status modification).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.infrastructure.db.models.project import ProjectRecord
from backend.infrastructure.db.models.user import UserRecord
from backend.providers.admin_dtos import (
    AdminUserDetailDTO,
    AdminUserListItemDTO,
    AdminUserProjectDTO,
    UpdateRoleDTO,
    UpdateStatusDTO,
)
from backend.providers.admin_user_provider import AdminUserProvider


class PostgresAdminUserAdapter(AdminUserProvider):
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    def list_users(
        self, search: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[AdminUserListItemDTO]:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            stmt = select(UserRecord)
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    UserRecord.email.ilike(pattern) | UserRecord.display_name.ilike(pattern)
                )
            stmt = stmt.order_by(UserRecord.created_at.desc()).offset(offset).limit(limit)
            records = session.execute(stmt).scalars().all()

            result: list[AdminUserListItemDTO] = []
            for record in records:
                project_count = self._count_projects(session, record.id)
                result.append(_user_to_list_item(record, project_count))
            return result

    def count_users(self) -> int:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            return session.execute(select(func.count()).select_from(UserRecord)).scalar_one()

    def count_admin_users(self) -> int:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            return session.execute(
                select(func.count()).select_from(UserRecord).where(UserRecord.role == "admin")
            ).scalar_one()

    def get_user_detail(self, user_id: str) -> AdminUserDetailDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.get(UserRecord, user_id)
            if record is None:
                return None
            projects = self._list_projects(session, user_id)
            return _user_to_detail(record, projects)

    def update_user_role(self, user_id: str, dto: UpdateRoleDTO) -> AdminUserListItemDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            stmt = update(UserRecord).where(UserRecord.id == user_id).values(role=dto.role)
            result = session.execute(stmt)
            session.commit()
            if result.rowcount == 0:
                return None
            record = session.get(UserRecord, user_id)
            if record is None:
                return None
            project_count = self._count_projects(session, record.id)
            return _user_to_list_item(record, project_count)

    def update_user_status(self, user_id: str, dto: UpdateStatusDTO) -> AdminUserListItemDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            stmt = update(UserRecord).where(UserRecord.id == user_id).values(status=dto.status)
            result = session.execute(stmt)
            session.commit()
            if result.rowcount == 0:
                return None
            record = session.get(UserRecord, user_id)
            if record is None:
                return None
            project_count = self._count_projects(session, record.id)
            return _user_to_list_item(record, project_count)

    def _count_projects(self, session: Any, user_id: str) -> int:
        return session.execute(
            select(func.count())
            .select_from(ProjectRecord)
            .where(ProjectRecord.owner_user_id == user_id)
        ).scalar_one()

    def _list_projects(self, session: Any, user_id: str) -> list[AdminUserProjectDTO]:
        stmt = (
            select(ProjectRecord)
            .where(ProjectRecord.owner_user_id == user_id)
            .order_by(ProjectRecord.created_at.desc())
        )
        records = session.execute(stmt).scalars().all()
        return [
            AdminUserProjectDTO(
                id=r.id,
                name=r.name,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in records
        ]


def _user_to_list_item(record: UserRecord, project_count: int = 0) -> AdminUserListItemDTO:
    return AdminUserListItemDTO(
        id=record.id,
        email=record.email,
        display_name=record.display_name,
        role=record.role,
        status=record.status,
        project_count=project_count,
        last_login_at=record.last_login_at.isoformat() if record.last_login_at else None,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


def _user_to_detail(record: UserRecord, projects: list[AdminUserProjectDTO]) -> AdminUserDetailDTO:
    return AdminUserDetailDTO(
        id=record.id,
        email=record.email,
        display_name=record.display_name,
        role=record.role,
        status=record.status,
        project_count=len(projects),
        projects=projects,
        last_login_at=record.last_login_at.isoformat() if record.last_login_at else None,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )
