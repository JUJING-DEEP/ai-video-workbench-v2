from fastapi.testclient import TestClient

from app.main import app


def test_cors_allows_localhost_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/api/video-workbench/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_untrusted_origin():
    client = TestClient(app)

    response = client.options(
        "/api/video-workbench/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
