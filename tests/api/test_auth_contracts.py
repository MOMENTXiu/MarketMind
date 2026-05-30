"""Auth API contract tests for registration, login, current user, and SSE tickets."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_providers
from backend.business.pipelines.login_user_pipeline import LoginUserPipeline
from backend.business.pipelines.register_user_pipeline import RegisterUserPipeline
from backend.main import app
from backend.providers.auth_dtos import UserRegistrationInputDTO
from backend.providers.container import ProvidersContainer
from tests.fakes.auth_providers import (
    FakeAuthTokenProvider,
    FakePasswordHasherProvider,
    FakeSseTicketProvider,
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
    sse = FakeSseTicketProvider()
    repository = FakeProjectRepositoryProvider()
    return {
        "directory": directory,
        "hasher": hasher,
        "token": token,
        "sse": sse,
        "repository": repository,
    }


def _build_container(providers_dict):
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
        telemetry=type(
            "F",
            (),
            {
                "emit_debug": lambda *a, **k: None,
                "emit_audit": lambda *a, **k: None,
                "emit_error": lambda *a, **k: None,
            },
        )(),
        user_directory=providers_dict["directory"],
        password_hasher=providers_dict["hasher"],
        auth_token=providers_dict["token"],
        sse_ticket=providers_dict["sse"],
    )


def _register_user(providers_dict, email, password):
    container = _build_container(providers_dict)
    pipeline = RegisterUserPipeline(container)
    return pipeline.execute(UserRegistrationInputDTO(email=email, password=password))


def _login_user(providers_dict, email, password):
    container = _build_container(providers_dict)
    pipeline = LoginUserPipeline(container)
    return pipeline.execute(email, password)


def test_register_success(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == "test@example.com"


def test_register_duplicate_email(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    response = client.post(
        "/api/auth/register", json={"email": "test@example.com", "password": "otherpass"}
    )
    assert response.status_code == 409


def test_login_success(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    _register_user(auth_providers, "test@example.com", "password123")
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_login_invalid_password(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    _register_user(auth_providers, "test@example.com", "password123")
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpass",
        },
    )
    assert response.status_code == 401


def test_login_unknown_email(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401


def test_me_success(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    _register_user(auth_providers, "test@example.com", "password123")
    user, token_pair = _login_user(auth_providers, "test@example.com", "password123")
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token_pair.access_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "test@example.com"


def test_me_missing_token(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_bad_token(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"})
    assert response.status_code == 401


def test_me_expired_token(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    user = _register_user(auth_providers, "test@example.com", "password123")
    from backend.providers.auth_dtos import AuthTokenClaimsDTO

    token = auth_providers["token"].make_expired_token(
        AuthTokenClaimsDTO(sub=user.id, email=user.email, display_name=None)
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_logout_requires_auth(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.post("/api/auth/logout")
    assert response.status_code == 401


def test_sse_ticket_success(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    _register_user(auth_providers, "test@example.com", "password123")
    user, token_pair = _login_user(auth_providers, "test@example.com", "password123")
    response = client.post(
        "/api/auth/sse-ticket",
        headers={"Authorization": f"Bearer {token_pair.access_token}"},
        json={
            "resource_type": "project",
            "resource_id": "proj-1",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "ticket" in data


def test_sse_ticket_requires_auth(client: TestClient, auth_providers):
    app.dependency_overrides[get_providers] = lambda: _build_container(auth_providers)
    response = client.post(
        "/api/auth/sse-ticket",
        json={
            "resource_type": "project",
            "resource_id": "proj-1",
        },
    )
    assert response.status_code == 401
