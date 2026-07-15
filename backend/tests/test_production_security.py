import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import PRODUCTION_BACKEND_HOST, PRODUCTION_FRONTEND_ORIGIN, Settings
from app.main import create_app


def production_settings(**overrides) -> Settings:
    values = {
        "app_environment": "production",
        "debug": False,
        "database_url": "postgresql+psycopg2://user:password@db.example/novoriq",
        "jwt_secret_key": "a-production-only-secret-that-is-long-enough",
        "frontend_url": PRODUCTION_FRONTEND_ORIGIN,
        "backend_public_url": "https://novoriq-reconciliation-platform.onrender.com",
        "backend_cors_origins": [PRODUCTION_FRONTEND_ORIGIN],
        "allowed_hosts": [PRODUCTION_BACKEND_HOST],
        "whop_webhook_enabled": False,
        "whop_membership_sync_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def client() -> TestClient:
    application = create_app(production_settings())

    @application.get("/_test/auth-failure")
    def auth_failure():
        raise HTTPException(status_code=401, detail="Unauthorized")

    @application.get("/_test/error")
    def application_error():
        raise RuntimeError("sensitive internal detail")

    return TestClient(application, base_url=f"https://{PRODUCTION_BACKEND_HOST}", raise_server_exceptions=False)


def test_allowed_origin_preflight_and_authorization_header() -> None:
    response = client().options(
        "/auth/login",
        headers={
            "Origin": PRODUCTION_FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PRODUCTION_FRONTEND_ORIGIN
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize("origin", ["https://malicious.example", f"{PRODUCTION_FRONTEND_ORIGIN}/", "http://localhost:3000"])
def test_disallowed_production_origins(origin: str) -> None:
    response = client().options(
        "/auth/login",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_cors_is_present_on_validation_auth_and_application_errors() -> None:
    test_client = client()
    headers = {"Origin": PRODUCTION_FRONTEND_ORIGIN}
    validation = test_client.post("/auth/register", json={}, headers=headers)
    unauthorized = test_client.get("/_test/auth-failure", headers=headers)
    failure = test_client.get("/_test/error", headers=headers)
    assert validation.status_code == 422
    assert unauthorized.status_code == 401
    assert failure.status_code == 500
    for response in (validation, unauthorized, failure):
        assert response.headers["access-control-allow-origin"] == PRODUCTION_FRONTEND_ORIGIN
        assert response.headers.get("x-request-id")
    assert failure.json()["detail"]["code"] == "INTERNAL_ERROR"
    assert "sensitive internal detail" not in failure.text


def test_unknown_host_is_rejected() -> None:
    response = client().get("/health", headers={"Host": "malicious.example"})
    assert response.status_code == 400


def test_development_origins_are_separate() -> None:
    settings = Settings(_env_file=None, app_environment="development")
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


@pytest.mark.parametrize(
    "override",
    [
        {"backend_cors_origins": ["*"]},
        {"jwt_secret_key": "change-this-in-production"},
        {"database_url": ""},
        {"allowed_hosts": ["*"]},
        {"debug": True},
    ],
)
def test_invalid_production_configuration_fails_fast(override: dict) -> None:
    with pytest.raises(RuntimeError):
        production_settings(**override).validate_production()
