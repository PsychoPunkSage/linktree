import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

@pytest.fixture
def app():
    from routers.admin import router
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)

def test_admin_without_cookie_returns_404(client):
    resp = client.get("/admin")
    assert resp.status_code == 404

def test_admin_auth_with_wrong_key_returns_404(client):
    resp = client.get("/admin/auth?key=wrongkey")
    assert resp.status_code == 404

def test_admin_auth_with_correct_key_sets_cookie(client):
    from config import settings
    resp = client.get(f"/admin/auth?key={settings.admin_secret}",
                      follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "pps_admin" in resp.headers.get("set-cookie", "")
