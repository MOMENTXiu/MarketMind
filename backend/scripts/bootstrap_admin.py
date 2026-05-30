"""One-shot admin bootstrap script.

Usage:
    ADMIN_BOOTSTRAP_EMAIL=admin@example.com uv run python -m backend.scripts.bootstrap_admin

Promotes an existing user to admin role. Not a runtime HTTP API — intended
for local setup and deployment initialization.
"""

from __future__ import annotations

import os

from sqlalchemy import update

from backend.core.config import settings as app_settings
from backend.infrastructure.db.models.user import UserRecord
from backend.infrastructure.db.session import create_db_engine, create_session_factory


def bootstrap_admin(email: str) -> None:
    """Promote the user with the given email to admin role."""
    engine = create_db_engine(app_settings)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        stmt = (
            update(UserRecord).where(UserRecord.email == email.lower().strip()).values(role="admin")
        )
        result = session.execute(stmt)
        session.commit()

        if result.rowcount == 0:
            print(f"No user found with email {email}")
        else:
            print(f"User {email} promoted to admin (rows updated: {result.rowcount})")


def main() -> None:
    email = os.environ.get("ADMIN_BOOTSTRAP_EMAIL")
    if not email:
        print("Error: ADMIN_BOOTSTRAP_EMAIL environment variable is not set")
        print(
            "Usage: ADMIN_BOOTSTRAP_EMAIL=admin@example.com uv run python -m backend.scripts.bootstrap_admin"
        )
        raise SystemExit(1)

    bootstrap_admin(email)


if __name__ == "__main__":
    main()
