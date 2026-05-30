"""Admin Console auth dependencies.

require_admin_user: JWT proves identity, DB role proves authorization.
Role from token claims is never trusted for authorization decisions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.dependencies import get_providers
from backend.business.pipelines.resolve_current_user_pipeline import ResolveCurrentUserPipeline
from backend.core.errors import (
    AuthError,
    DisabledUserError,
    ExpiredTokenError,
    InvalidTokenError,
    NotFoundError,
)
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

_http_bearer = HTTPBearer(auto_error=False)


async def require_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    providers: ProvidersContainer = Depends(get_providers),
) -> AuthenticatedUserContext:
    """Require valid JWT + admin role.

    IMPORTANT: admin role is determined by DB lookup in
    ResolveCurrentUserPipeline, NOT by trusting JWT role claim.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        pipeline = ResolveCurrentUserPipeline(providers)
        user_ctx = pipeline.execute(credentials.credentials)
    except (InvalidTokenError, ExpiredTokenError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DisabledUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    # Authorization: DB role must be 'admin'
    if user_ctx.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return user_ctx
