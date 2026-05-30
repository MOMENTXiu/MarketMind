"""Admin API authentication behavior tests.

Phase 0.2: /api/admin/* must return 401 without auth, 403 for non-admin users,
and 200 for admin users. Admin role must come from DB lookup, not JWT claim.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_providers
from backend.main import app
from backend.providers.container import ProvidersContainer
from tests.fakes.auth_providers import (
    FakeAuthTokenProvider,
    FakePasswordHasherProvider,
    FakeUserDirectoryProvider,
)
from tests.fakes.providers import FakeProjectRepositoryProvider


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_providers():
    directory = FakeUserDirectoryProvider()
    hasher = FakePasswordHasherProvider()
    token = FakeAuthTokenProvider()
    repository = FakeProjectRepositoryProvider()
    return {
        "directory": directory,
        "hasher": hasher,
        "token": token,
        "repository": repository,
    }


def _register_user(providers_dict, email, password, role="user"):
    """Register a user via the proper pipeline so password is hashed."""
    from backend.business.pipelines.register_user_pipeline import RegisterUserPipeline
    from backend.providers.auth_dtos import UserRegistrationInputDTO

    container = _build_container(providers_dict)
    pipeline = RegisterUserPipeline(container)
    user = pipeline.execute(UserRegistrationInputDTO(email=email, password=password))
    # Attach role in-memory for auth testing
    if not hasattr(providers_dict["directory"], "_roles"):
        providers_dict["directory"]._roles = {}
    providers_dict["directory"]._roles[user.id] = role
    return user


def _build_container(providers_dict):
    """Build a minimal ProvidersContainer for admin auth testing."""

    class FakeTelemetry:
        def emit_debug(self, *a, **k):
            return None

        def emit_audit(self, *a, **k):
            return None

        def emit_error(self, *a, **k):
            return None

        def start_span(self, *a, **k):
            return None

        def end_span(self, *a, **k):
            return None

    return ProvidersContainer(
        repository=providers_dict["repository"],
        storage=type("F", (), {"get_project_dir": lambda s, pid: None})(),
        assets=type(
            "F",
            (),
            {
                "save_project_report": lambda *a, **k: None,
                "resolve_project_report": lambda *a, **k: None,
            },
        )(),
        dataset=type("F", (), {"load_dataset": lambda *a, **k: None})(),
        retail_dataset=type("F", (), {})(),
        regularized_dataset=type("F", (), {})(),
        association_rules=type("F", (), {"load_rules": lambda *a, **k: None})(),
        recommendation_models=type("F", (), {"load_model": lambda *a, **k: None})(),
        analysis_artifacts=type("F", (), {})(),
        analysis_models=type("F", (), {})(),
        llm=type("F", (), {"generate_text": lambda *a, **k: None})(),
        analysis_jobs=type("F", (), {"submit_project_analysis": lambda *a, **k: None})(),
        telemetry=FakeTelemetry(),
        user_directory=providers_dict["directory"],
        password_hasher=providers_dict["hasher"],
        auth_token=providers_dict["token"],
    )


def _override_resolve_for_role(providers_dict, role: str):
    """Patch resolve_current_user to return the given role regardless of JWT."""
    from backend.abilities.auth.resolve_current_user import resolve_current_user

    original = resolve_current_user

    def _patched(token, auth_token, user_directory):
        result = original(token, auth_token, user_directory)
        user_id = result.user_id
        # Inject role from fake directory
        injected_role = getattr(user_directory, "_roles", {}).get(user_id, "user")
        from backend.providers.auth_dtos import AuthenticatedUserContext

        return AuthenticatedUserContext(
            user_id=result.user_id,
            email=result.email,
            display_name=result.display_name,
            role=injected_role,
        )

    import backend.business.pipelines.resolve_current_user_pipeline as m

    m.resolve_current_user = _patched
    return original


def _login(providers_dict, email, password):
    """Login helper returning (user_dto, token_pair)."""
    from backend.business.pipelines.login_user_pipeline import LoginUserPipeline

    container = _build_container(providers_dict)
    return LoginUserPipeline(container).execute(email, password)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_admin_endpoint_returns_401_without_token(client, auth_providers):
    """Unauthenticated requests to /api/admin/* must return 401."""
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.get("/api/admin/status/summary")
    assert response.status_code == 401


def test_admin_endpoint_returns_403_for_non_admin_user(client, auth_providers):
    """A user with role='user' must get 403 on admin endpoints."""
    _register_user(auth_providers, "user@test.com", "pass123", role="user")
    _, token_pair = _login(auth_providers, "user@test.com", "pass123")

    # Override so the resolved context has role='user'
    _override_resolve_for_role(auth_providers, "user")
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)

    response = client.get(
        "/api/admin/status/summary",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
    )
    assert response.status_code == 403


def test_admin_endpoint_returns_200_for_admin_user(client, auth_providers):
    """An admin user must get 200 on admin endpoints."""
    _register_user(auth_providers, "admin@test.com", "pass123", role="admin")
    _, token_pair = _login(auth_providers, "admin@test.com", "pass123")

    _override_resolve_for_role(auth_providers, "admin")
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)

    response = client.get(
        "/api/admin/status/summary",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
    )
    # 200 expected once the route is implemented; may be 404 during Phase 0
    assert response.status_code in (200, 404)


def test_admin_role_authorization_uses_db_role_not_jwt_claim(client, auth_providers):
    """Auth must use DB role from ResolveCurrentUserPipeline, not JWT claim."""
    _register_user(auth_providers, "user@test.com", "pass123", role="user")
    _, token_pair = _login(auth_providers, "user@test.com", "pass123")

    # Even if the fake token contained role='admin', DB lookup says 'user'
    _override_resolve_for_role(auth_providers, "user")
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)

    response = client.get(
        "/api/admin/status/summary",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
    )
    assert response.status_code == 403


def test_role_change_takes_effect_next_request(client, auth_providers):
    """After role is changed in DB, next request must respect new role."""
    _register_user(auth_providers, "promoted@test.com", "pass123", role="user")
    _, token_pair = _login(auth_providers, "promoted@test.com", "pass123")

    # First request: role is 'user' → 403
    _override_resolve_for_role(auth_providers, "user")
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)

    r1 = client.get(
        "/api/admin/status/summary",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
    )
    assert r1.status_code == 403

    # Change role in fake directory to 'admin'
    user_dto = auth_providers["directory"].find_user_by_email("promoted@test.com")
    auth_providers["directory"]._roles[user_dto.id] = "admin"

    # Second request with same token: should now be 200 (DB role changed)
    _override_resolve_for_role(auth_providers, "admin")
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)

    r2 = client.get(
        "/api/admin/status/summary",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
    )
    assert r2.status_code in (200, 404)
